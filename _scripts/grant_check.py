#!/usr/bin/env python3
"""grant_check.py — check the catalog's claims against the live GitHub profile.

GitHub exposes achievement data through no API, public or authenticated. The
only authoritative source is the HTML of a public profile page, where earned
badges render as images. So this is a scraper, and a scraper's first duty is to
distinguish "the page says there is no badge" from "we failed to read the page".

Those two cases look identical if you only count badges. On 2026-10-03 three of
nine statuses in this catalog were wrong for exactly that reason. The
distinctions that matter, and where they are enforced here:

- `looks_like_profile` refuses to interpret a page that is not a profile. A
  login wall or an error page has no badges either, and reading it as "none
  earned" turns a transient failure into a false audit finding.
- `count_achievement_cards` counts badge *cards* separately from parsed
  *badges*. Cards present but nothing parsed means the asset naming changed, and
  reporting that as drift would name every achievement in the catalog as
  unearned.
- Zero cards and zero badges is a legitimate empty state, not a parse failure.
  An account with no badges must not be indistinguishable from a broken parser.

Exit codes:
    0  the catalog agrees with the live profile
    1  the live profile could not be determined, or the CLI was misused
    2  the catalog and the live profile disagree

Usage:
    python _scripts/grant_check.py [login]
    python _scripts/grant_check.py --json
    python _scripts/grant_check.py --catalog _achievements
    python _scripts/grant_check.py --catalog _achievements --quiet
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPT_DIR = Path(__file__).parent

sys.path.insert(0, str(SCRIPT_DIR))
from _utils import scrub_sensitive  # noqa: E402

with suppress(AttributeError, ValueError):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_CATALOG = REPO_ROOT / "_achievements"
DEFAULT_ACCOUNT = "neohiro"
USER_AGENT = "neohiro-achievement-hacks (+https://github.com/neohiro/achievement-hacks)"

# Kept in step with list_achievements.VALID_STATUSES by test. Both tools need the
# vocabulary: this one to classify a status it is handed, the other to reject a
# meta.yaml that cannot be classified.
VALID_STATUSES = {"Not yet", "In progress", "Earned", "Deprecated", "Unobtainable"}

# Verdicts that are agreement. Everything else is drift.
CLEAN_VERDICTS = {"earned", "not-yet", "not-earnable"}

# Verdicts that mean "the catalog and the profile agree, and here is what each
# said". Distinct from CLEAN_VERDICTS, which is only about the verdict *name*:
# `earned` is agreement, but a row showing it is still worth printing, because
# the live tier is evidence and evidence is the point of an audit. An empty
# table therefore means "nothing to look at", not "nothing was checked".
REPORTABLE_VERDICTS = CLEAN_VERDICTS | {"contradiction"}

# A GitHub login: alphanumerics and single hyphens, no leading or trailing
# hyphen, 1-39 characters. This is validated rather than trusted because the
# value is interpolated into a URL, and an unchecked argument is a request
# forgery waiting for a stray "#" or "/".
LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")

# Badge assets are named `<slug>-<tier>-<hash>.png`, but the hash is a content
# digest that changes when GitHub re-renders the badge, so it cannot be part of
# the match. Anchored on the asset host and path so a badge referenced from a
# third-party CDN is not mistaken for one of ours.
ASSET_RE = re.compile(
    r"github\.githubassets\.com/assets/"
    r"(?P<stem>[a-z0-9-]+?)-(?P<digest>[0-9a-f]{4,})\.png",
    re.IGNORECASE,
)

# The tier label GitHub renders on a repeatable badge, e.g. "x3".
TIER_COUNT_RE = re.compile(r"achievement-tier-label[^>]*>\s*x(?P<count>\d+)", re.IGNORECASE)

# A badge card is an <a> pointing at the profile's achievements tab.
CARD_RE = re.compile(r"<a\s[^>]*href=\"[^\"]*[?&]achievement=[^\"]*\"", re.IGNORECASE)

TIER_RANK = {"default": 0, "bronze": 1, "silver": 2, "gold": 3}

# Tier suffixes, longest-first by length is irrelevant here since the match is
# anchored at the end, but the explicit list keeps the order readable.
TIER_NAMES = ("default", "bronze", "silver", "gold")

# HTTP statuses worth retrying. 429 is GitHub's rate limit; 5xx are transient.
# 404 is deliberately absent: a 404 means the account does not exist, and
# retrying it three times just delays an error that will not change.
RETRY_STATUSES = {429, 500, 502, 503, 504}


class CatalogError(Exception):
    """Something the caller can act on: a bad login, an unfetchable profile, a
    malformed catalog entry. Distinct from a traceback because every one of these
    is an expected outcome with a message worth reading."""


@dataclass(frozen=True)
class EarnedBadge:
    """One badge seen on the profile page."""

    slug: str
    tier: str
    count: str | None = None


@dataclass(frozen=True)
class CatalogEntry:
    """One row of the catalog, as the auditor sees it.

    `earnable` is kept as the string it is in the source (`"true"` / `"false"`)
    so a malformed value can be reported as malformed. Coercing it to a bool
    first would turn `'true'` into `True` and quietly agree with a typo.
    """

    slug: str
    status: str
    earnable: str
    path: str


@dataclass
class AuditRow:
    """One catalog entry compared against the profile."""

    slug: str
    claimed_status: str
    earnable: str
    live_tier: str | None
    live_count: str | None
    verdict: str
    detail: str = ""


@dataclass
class _Counters:
    requests: int = field(default=0)


def validate_login(login: str) -> str:
    """Return `login` unchanged, or raise CatalogError explaining why not."""
    if not isinstance(login, str) or not LOGIN_RE.match(login):
        raise CatalogError(
            f"{login!r} is not a valid GitHub login. A login is 1-39 characters "
            f"of letters, digits and single hyphens, and cannot start or end "
            f"with a hyphen."
        )
    return login


def fetch_profile_html(
    login: str,
    attempts: int = 3,
    backoff: float = 1.0,
    sleep=time.sleep,
    timeout: int = 30,
) -> str:
    """Fetch https://github.com/<login>, retrying transient failures.

    `sleep`, `backoff` and `timeout` are injectable so the retry policy can be
    tested without spending real seconds.

    Returns the response body. Whether that body is *interpretable* is not
    decided here: this function owns transport policy - retry the transient,
    do not retry the 404, report exhaustion - and the caller owns the content
    judgement, because only the caller knows whether a page it does not
    recognise is an interstitial to refuse or a profile whose markup changed.
    `main()` therefore calls `looks_like_profile()` itself and reports the
    refusal in the audit's own voice.

    Raises CatalogError on a permanent failure and on exhausted retries.
    """
    validate_login(login)
    url = f"https://github.com/{login}"
    last: Exception | None = None

    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise CatalogError(
                    f"404: GitHub account {login!r} does not exist"
                ) from exc
            if exc.code not in RETRY_STATUSES:
                raise CatalogError(
                    f"HTTP {exc.code} fetching {url}: {scrub_sensitive(str(exc.reason))}"
                ) from exc
            last = exc
        except urllib.error.URLError as exc:
            # DNS failure, connection refused, timeout. All plausibly transient.
            last = exc
        else:
            return body

        if attempt < attempts:
            # The first wait is `backoff / 2`, then it doubles. Starting at
            # `backoff` would make the first retry wait longer than the whole
            # call it is retrying, which is the opposite of what a backoff is
            # for. With the default of 1.0 that is 0.5s, 1.0s, 2.0s.
            sleep(backoff * (2 ** (attempt - 2)))

    raise CatalogError(
        f"could not fetch {url} after {attempts} attempt"
        f"{'' if attempts == 1 else 's'}: {scrub_sensitive(str(last))}"
    )


def looks_like_profile(html: str) -> bool:
    """True when `html` is plausibly a profile page.

    Two positive signals, because either alone is too weak:
    `tab=achievements` (the profile nav links to it even with zero badges) and
    the `achievement-badge-sidebar` container. An empty sidebar still counts,
    which is what keeps a genuinely badge-free account from being mistaken for a
    parse failure.
    """
    if not html:
        return False
    if re.search(r"tab=achievements", html, re.IGNORECASE):
        return True
    if "achievement-badge-sidebar" in html:
        return True
    return False


def count_achievement_cards(html: str) -> int:
    """Count badge cards, independently of whether any badge can be parsed.

    The comparison `count_achievement_cards(html) > 0` against
    `len(parse_badges(html)) > 0` is the parser-break guard, and counting from
    the anchor rather than the asset is what makes it work: a CDN change breaks
    asset parsing while leaving the markup's shape intact.
    """
    return len(CARD_RE.findall(html or ""))


def _known_slugs() -> list[str]:
    """Every slug the catalog knows, longest first.

    Read from the catalog rather than hardcoded, because a hardcoded list is
    correct on the day it is written and silently stale afterwards - and a stale
    list makes an unrecognised badge look like a *different* achievement rather
    than an unknown one.
    """
    global _KNOWN_SLUGS
    if _KNOWN_SLUGS is None:
        slugs: list[str] = []
        for meta_path in sorted(DEFAULT_CATALOG.rglob("meta.yaml")):
            try:
                import yaml

                data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 - a bad file must not break parsing
                continue
            if isinstance(data, dict) and isinstance(data.get("slug"), str):
                slugs.append(data["slug"].lower())
        # Longest first so `heart-on-your-sleeve` is tried before `heart-on`.
        _KNOWN_SLUGS = sorted(set(slugs), key=len, reverse=True)
    return _KNOWN_SLUGS


_KNOWN_SLUGS: list[str] | None = None


def _resolve_asset_slug(stem: str, tier: str = "") -> tuple[str, str] | None:
    """Split an asset filename stem into (slug, tier), or None if unrecognised.

    `stem` is the filename minus its content digest, so it is
    `<slug>[-<tier>]` with the tier present for multi-tier badges and absent for
    single-tier ones.

    Resolution order matters and is longest-slug-first: `heart-on-your-sleeve-gold`
    has to be read as the slug `heart-on-your-sleeve` plus tier `gold`, and
    matching the slug greedily before stripping the tier splits it as
    `heart-on` + `your-sleeve`. A single-tier slug such as `quickdraw` has no
    tier suffix at all, which is why the tier is stripped before the slug match
    and defaults to `default` afterwards.
    """
    for slug in _known_slugs():
        if stem == slug:
            return slug, tier or "default"
    for slug in _known_slugs():
        if stem.startswith(slug + "-"):
            rest = stem[len(slug) + 1 :]
            if rest in TIER_NAMES:
                return slug, rest
            if tier:
                return slug, tier
            return None
    # Unknown to the catalog. If the stem ends in a tier name, the slug is the
    # remainder - this is how a newly-issued achievement is reported as
    # `uncatalogued` rather than silently dropped.
    for name in TIER_NAMES:
        if stem.endswith("-" + name):
            candidate = stem[: -(len(name) + 1)]
            if candidate:
                return candidate, name
    return None


def parse_badges(html: str) -> dict[str, EarnedBadge]:
    """Extract earned badges from profile HTML.

    The slug comes from the card's own anchor when it names one, falling back to
    the asset filename. The asset is the fallback rather than the primary
    because a multi-word slug is ambiguous when read from a filename alone -
    `heart-on-your-sleeve-gold` could be any of several splits, and the anchor
    is unambiguous.
    """
    if not html:
        return {}

    found: dict[str, EarnedBadge] = {}
    for match in re.finditer(
        r"<a\s[^>]*href=\"(?P<href>[^\"]*[?&]achievement=(?P<slug_href>[a-z0-9-]+)[^\"]*)\""
        r"(?P<body>.*?)</a>",
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        anchor_slug = match.group("slug_href").lower()
        slug = anchor_slug
        body = match.group("body")

        asset = ASSET_RE.search(body)
        tier = ""
        if asset:
            resolved = _resolve_asset_slug(asset.group("stem").lower())
            if resolved is None:
                # A card whose asset we cannot attribute to any slug. Skipping it
                # is correct: `count_achievement_cards` still counts the card, so
                # a systematic failure here trips the parser-break guard rather
                # than reporting every catalog entry as unearned.
                continue
            # The asset wins over the anchor. The anchor is a query parameter
            # GitHub fills from the same slug, so when the two disagree the
            # asset is the one that is actually rendering - which is how a card
            # whose anchor says `wrong-slug` still resolves to `quickdraw`
            # instead of inventing an achievement nobody has earned.
            slug, tier = resolved
        else:
            # No recognisable GitHub badge asset inside this card. The anchor is
            # not enough on its own: it names the achievement the card is *for*,
            # so a card whose image comes from somewhere unexpected would be
            # read as a badge that was earned. GitHub's own card always carries a
            # digested githubassets.com filename, so requiring one is what makes
            # "cards present but nothing parsed" a meaningful signal rather than
            # a card we happened to read the anchor of.
            continue

        if not slug:
            continue
        if not tier:
            tier = "default"

        count_match = TIER_COUNT_RE.search(body)
        count = count_match.group("count") if count_match else None
        found[slug] = EarnedBadge(slug=slug, tier=tier, count=count)
    return found


def parse_catalog(base: str | Path = DEFAULT_CATALOG) -> list[CatalogEntry]:
    """Read every meta.yaml under `base` into a CatalogEntry.

    Deliberately independent of list_achievements.load_catalog: this tool is
    told about statuses, it does not define them, and a malformed entry has to
    be *reported as drift* rather than aborting the audit. An auditor that
    refuses to run because one entry is malformed cannot tell you that the entry
    is malformed.
    """
    root = Path(base)
    if not root.is_dir():
        raise CatalogError(f"catalog directory does not exist: {root}")

    entries: list[CatalogEntry] = []
    for meta_path in sorted(root.rglob("meta.yaml")):
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise CatalogError(
                "PyYAML is required; install it with "
                "`pip install -r requirements.txt`"
            ) from exc
        try:
            data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise CatalogError(f"{meta_path}: invalid YAML - {exc}") from exc
        if not isinstance(data, dict):
            raise CatalogError(f"{meta_path}: expected a mapping, got {type(data).__name__}")

        slug = data.get("slug")
        status = data.get("status")
        earnable = data.get("earnable")
        # Coerced to the string form deliberately. `True` becomes "true", so a
        # real boolean and the string "true" agree, while a string "false" or a
        # missing value stays distinguishable as malformed.
        earnable_text = (
            "true"
            if earnable is True
            else "false"
            if earnable is False
            else "(missing)"
            if earnable is None
            else str(earnable)
        )
        entries.append(
            CatalogEntry(
                slug=slug or meta_path.parent.name,
                status=status if isinstance(status, str) else str(status),
                earnable=earnable_text,
                path=str(meta_path),
            )
        )
    if not entries:
        raise CatalogError(f"no meta.yaml files found under {root}")
    return entries


def classify(entry: CatalogEntry, badge: EarnedBadge | None) -> tuple[str, str]:
    """Compare one catalog entry against one badge (or its absence).

    Returns (verdict, detail). Malformed input is a verdict of its own rather
    than an exception, so it shows up in the report next to the other findings
    instead of ending the run.

    The `Earned`-without-badge direction matters as much as the reverse: it is
    what catches someone switching off the public-profile achievement toggle,
    which would otherwise invalidate every claim in the catalog at once.
    """
    if entry.status not in VALID_STATUSES:
        return "malformed", (
            f"status {entry.status!r} is not one of {sorted(VALID_STATUSES)}"
        )
    if entry.earnable not in {"true", "false"}:
        return "malformed", f"earnable is {entry.earnable!r}, expected a boolean"

    if badge is not None:
        if entry.status == "Earned":
            return "earned", f"catalog says Earned, profile shows {badge.tier}"
        if entry.status == "Unobtainable" or entry.earnable == "false":
            return "contradiction", (
                f"catalog says {entry.status!r}/earnable={entry.earnable}, "
                f"profile shows {badge.tier}"
            )
        return "stale-not-earned", (
            f"catalog says {entry.status!r}, profile shows {badge.tier}"
        )

    if entry.status == "Earned":
        return "stale-earned", "catalog says Earned, profile shows no badge"
    if entry.status == "Unobtainable" or entry.earnable == "false":
        return "not-earnable", "unearnable and absent from the profile"
    return "not-yet", "not claimed, not present"


def audit(entries: list[CatalogEntry], badges: dict[str, EarnedBadge]) -> list[AuditRow]:
    """Compare every catalog entry to the profile, and the profile to the catalog.

    Both directions. A badge the catalog does not mention is drift too - it means
    someone earned something this repository does not track, and the catalog's
    claim to be comprehensive is stale.
    """
    rows: list[AuditRow] = []
    seen: set[str] = set()

    for entry in entries:
        badge = badges.get(entry.slug)
        seen.add(entry.slug)
        verdict, detail = classify(entry, badge)
        rows.append(
            AuditRow(
                slug=entry.slug,
                claimed_status=entry.status,
                earnable=entry.earnable,
                live_tier=badge.tier if badge else None,
                live_count=badge.count if badge else None,
                verdict=verdict,
                detail=detail,
            )
        )

    for slug, badge in sorted(badges.items()):
        if slug in seen:
            continue
        rows.append(
            AuditRow(
                slug=slug,
                claimed_status="(uncatalogued)",
                earnable="(unknown)",
                live_tier=badge.tier,
                live_count=badge.count,
                verdict="uncatalogued",
                detail=(
                    f"profile shows {badge.tier} for an achievement this "
                    f"repository does not track"
                ),
            )
        )
    return rows


def drift_rows(rows: list[AuditRow]) -> list[AuditRow]:
    """The rows that disagree with reality."""
    return [r for r in rows if r.verdict not in CLEAN_VERDICTS]


def render_table(rows: list[AuditRow]) -> str:
    """Render drift rows as an aligned plain-text table.

    Width is computed from the data rather than fixed, so a long slug does not
    wrap into the next column and read as two values.
    """
    headers = ("SLUG", "CLAIMED", "LIVE", "VERDICT", "DETAIL")
    # Rows that agree are shown too. An audit that prints nothing on success
    # cannot be distinguished from one that never ran, and the live tier on an
    # `earned` row is the evidence the catalog's `verified:` block cites.
    shown = [r for r in rows if r.verdict in REPORTABLE_VERDICTS] or drift_rows(rows)
    body = [
        (
            row.slug,
            row.claimed_status,
            f"{row.live_tier} x{row.live_count}" if row.live_count else (row.live_tier or "-"),
            row.verdict,
            row.detail,
        )
        for row in shown
    ]
    widths = [
        max(len(headers[i]), max((len(cells[i]) for cells in body), default=0))
        for i in range(len(headers))
    ]

    lines = [
        # strict=True: a row shorter than the header would silently truncate to
        # whatever it has, which is how a column goes missing from a report
        # nobody is looking at closely.
        "  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True)).rstrip(),
        "  ".join("-" * w for w in widths).rstrip(),
    ]
    if not body:
        # The header stays. A caller that gets "(no drift)" with nothing to
        # attach it to has to guess whether the check ran; a table with a header
        # and no rows says so unambiguously.
        lines.append("(no drift)")
    for cells in body:
        lines.append(
            "  ".join(c.ljust(w) for c, w in zip(cells, widths, strict=True)).rstrip()
        )
    return "\n".join(lines)


def _positive_int(value: str) -> int:
    """argparse type: a strictly positive integer.

    Zero and negatives are rejected rather than clamped. A timeout of 0 or a
    request budget of -1 is a mistake, and silently substituting a default hides
    it until something times out for an unrelated reason.
    """
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {number}")
    return number


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grant_check.py",
        description=(
            "Check the achievement catalog against the live GitHub profile."
        ),
    )
    parser.add_argument(
        "login",
        nargs="?",
        # None rather than DEFAULT_ACCOUNT so argparse itself records whether a
        # positional was typed. With a real default here, passing both a
        # positional and --account is indistinguishable from passing --account
        # alone, and the conflict below would never fire.
        default=None,
        help=f"GitHub login to audit (default: {DEFAULT_ACCOUNT})",
    )
    parser.add_argument(
        "--account",
        default=None,
        help="Alias for the positional login. Provided for call sites that pass "
        "the account as a flag.",
    )
    parser.add_argument(
        "--catalog",
        default=str(DEFAULT_CATALOG),
        metavar="DIR",
        help="Catalog root to audit against (default: _achievements).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON on stdout, and nothing else.")
    parser.add_argument("--quiet", action="store_true", help="Print the summary but not the drift table.")
    parser.add_argument(
        "--timeout",
        type=_positive_int,
        default=30,
        metavar="SECONDS",
        help="Per-request timeout (default: 30).",
    )
    parser.add_argument(
        "--attempts",
        type=_positive_int,
        default=3,
        metavar="N",
        help="How many times to try a transient failure (default: 3).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns an exit code; argparse still raises SystemExit for a
    usage error, which is the correct behaviour for a CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    login = args.account if args.account is not None else args.login

    if args.login is not None and args.account is not None:
        # Two accounts named, one of them silently discarded. `--account` winning
        # on its own is fine - that is its purpose - but dropping a login the
        # caller typed is how an audit of the wrong account looks clean.
        print(
            f"error: {args.login!r} and --account {args.account!r} both specify "
            f"an account; pass the login either positionally or with --account, "
            f"not both.",
            file=sys.stderr,
        )
        return 1

    if login is None:
        login = DEFAULT_ACCOUNT

    try:
        validate_login(login)
        entries = parse_catalog(args.catalog)
    except CatalogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        html = fetch_profile_html(
            login, attempts=args.attempts, timeout=args.timeout
        )
    except CatalogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not looks_like_profile(html):
        # A login wall, an error page, or changed markup. All three look like
        # "no badges", and all three would otherwise be reported as the entire
        # catalog being unearned.
        print(
            "Refusing to report drift: the page fetched for "
            f"@{login} does not look like a GitHub profile. It may be behind a "
            "login wall, rate-limited, or GitHub may have changed the markup. "
            "Reporting against it would name every achievement in the catalog "
            "as unearned.",
            file=sys.stderr,
        )
        return 1

    cards = count_achievement_cards(html)
    badges = parse_badges(html)

    # The parser-break guard. Cards present but nothing parsed means the asset
    # naming changed, and every row would otherwise be reported as drift -
    # naming the entire catalog as unearned on the strength of a CDN rename.
    if cards > 0 and not badges:
        print(
            f"error: found {cards} badge card(s) but parsed none. GitHub's badge "
            f"asset naming has probably changed. Update ASSET_RE, and the "
            f"slug/tier resolution beside it, in {Path(__file__).name}.",
            file=sys.stderr,
        )
        return 1

    rows = audit(entries, badges)
    drift = drift_rows(rows)
    # Always "ok" here, and that is the point. The parser-break guard above has
    # already returned 1 on "cards but no badges", so reaching this line *is* the
    # evidence that the parser is sane. The field is emitted so a `--json`
    # consumer can tell "audited and the parser is fine" from an older payload
    # that predates the guard and had no way to say so.
    parser_sanity = "ok"

    if args.json:
        payload = {
            "login": login,
            "catalog_entry_count": len(entries),
            "live_badge_count": len(badges),
            "cards_found": cards,
            "drift_count": len(drift),
            "parser_sanity": parser_sanity,
            "rows": [
                {
                    "slug": r.slug,
                    "claimed_status": r.claimed_status,
                    "earnable": r.earnable,
                    "live_tier": r.live_tier,
                    "live_count": r.live_count,
                    "verdict": r.verdict,
                    "detail": r.detail,
                }
                for r in rows
            ],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        # The human summary goes to stderr so stdout stays pipeable to jq.
        if drift:
            print(
                f"DRIFT: {len(drift)} of {len(entries)} catalog entries disagree "
                f"with @{login}'s live profile.",
                file=sys.stderr,
            )
        else:
            print(
                f"OK: catalog matches the live profile for @{login} "
                f"({len(entries)} entries, {len(badges)} live badges).",
                file=sys.stderr,
            )
        return 2 if drift else 0

    if not args.quiet:
        table = render_table(rows)
        if drift:
            print(table)
            print()

    if drift:
        print(
            f"DRIFT: {len(drift)} of {len(entries)} catalog entries disagree with "
            f"@{login}'s live profile."
        )
        return 2

    print(
        f"OK: catalog matches the live profile for @{login} "
        f"({len(entries)} entries, {len(badges)} live badges)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())