#!/usr/bin/env python3
"""grant_check.py - read-only audit of which GitHub Achievements an account holds.

This script NEVER writes to GitHub. It performs one unauthenticated GET of the
public profile page, parses the achievement badges GitHub renders there, and
compares them against the catalog in ``_achievements/*/meta.yaml``.

The point is to keep ``status:`` fields honest. Every status in this repo is a
manual claim; this script is the mechanical check that the claim still matches
reality, which makes the catalog safe to run in CI.

Usage:
    python grant_check.py                       # audit neohiro
    python grant_check.py --account someone     # audit another account
    python grant_check.py --json                # machine-readable output
    python grant_check.py --quiet               # only report drift

Exit codes:
    0  catalog is consistent with the live profile
    1  usage/network/catalog error
    2  drift detected (a meta.yaml status disagrees with the live profile)

Requires: Python 3.10+ stdlib only. No token, no scopes, no rate-limit cost.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
ACHIEVEMENTS_DIR = os.path.join(REPO_ROOT, "_achievements")

DEFAULT_ACCOUNT = "neohiro"
TIERS = ("default", "bronze", "silver", "gold")

# Mirrors _docs/STATUS_LEGEND.md. An unknown value is a catalog bug, not a
# status, so it gets reported rather than silently treated as "not yet".
VALID_STATUSES = {"Not yet", "In progress", "Earned", "Deprecated", "Unobtainable"}

# 404 means the account does not exist, which is a stable answer. Retrying it
# only delays the error.
RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})

USER_AGENT = "achievement-hacks-grant-check (read-only catalog audit)"

SLUG_RE = re.compile(r"^slug:\s*(?P<v>[A-Za-z0-9._-]+)\s*$")
STATUS_RE = re.compile(r"^status:\s*(?P<v>.+?)\s*$")
EARNABLE_RE = re.compile(r"^earnable:\s*(?P<v>.+?)\s*$")

CARD_SPLIT_RE = re.compile(r'<a href="/[^"]*\?achievement=')
ASSET_RE = re.compile(
    r"githubassets\.com/assets/(?P<slug>[a-z0-9-]+?)-(?P<tier>default|bronze|silver|gold)-[0-9a-f]+\.png"
)
TIER_LABEL_RE = re.compile(
    r"achievement-tier-label--(?P<tier>[a-z]+)[^\"]*\"[^>]*>(?P<count>[^<]*)<"
)

# GitHub logins: 1-39 chars, alphanumerics and single hyphens, no leading or
# trailing hyphen. Enforced so a malformed --account fails cleanly instead of
# escaping as an http.client.InvalidURL traceback.
LOGIN_RE = re.compile(r"^(?![-])(?!.*[-]$)[A-Za-z0-9-]{1,39}$")


class CatalogError(RuntimeError):
    """Raised when the on-disk achievement catalog cannot be read."""


@dataclass
class CatalogEntry:
    slug: str
    status: str
    earnable: str
    path: str


@dataclass
class EarnedBadge:
    slug: str
    tier: str
    count: str | None = None


@dataclass
class AuditRow:
    slug: str
    claimed_status: str
    earnable: str
    live_tier: str | None
    live_count: str | None
    verdict: str
    detail: str = ""


def parse_catalog(achievements_dir: str = ACHIEVEMENTS_DIR) -> list[CatalogEntry]:
    """Read every meta.yaml under the catalog root.

    Only the handful of top-level scalar keys this audit needs are parsed, which
    keeps the script dependency-free. Nested ``tiers:`` blocks are skipped
    because they are indented and never match the anchored patterns.
    """
    entries: list[CatalogEntry] = []
    if not os.path.isdir(achievements_dir):
        raise CatalogError(f"catalog directory not found: {achievements_dir}")

    for dirpath, dirnames, filenames in os.walk(achievements_dir):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        if "meta.yaml" not in filenames:
            continue
        path = os.path.join(dirpath, "meta.yaml")
        slug = status = earnable = None
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if slug is None:
                    match = SLUG_RE.match(line)
                    if match:
                        slug = match.group("v")
                        continue
                if status is None:
                    match = STATUS_RE.match(line)
                    if match:
                        status = match.group("v")
                        continue
                if earnable is None:
                    match = EARNABLE_RE.match(line)
                    if match:
                        earnable = match.group("v")
                        continue
        if slug is None:
            raise CatalogError(f"{path}: no top-level 'slug:' key")
        entries.append(
            CatalogEntry(
                slug=slug,
                status=status if status is not None else "(missing)",
                earnable=earnable if earnable is not None else "(missing)",
                path=os.path.relpath(path, REPO_ROOT).replace("\\", "/"),
            )
        )

    if not entries:
        raise CatalogError(f"no meta.yaml files found under {achievements_dir}")
    entries.sort(key=lambda e: e.slug)
    return entries


def parse_badges(html: str) -> dict[str, EarnedBadge]:
    """Extract earned achievement badges from a rendered GitHub profile page.

    GitHub has no public API for achievements. The profile sidebar is the only
    machine-readable surface, and it encodes the tier in the badge asset
    filename (for example ``pull-shark-silver-<hash>.png``) with an optional
    count badge for achievements that can be earned more than once.

    A profile with no achievements, or a layout change that hides the sidebar,
    both yield an empty dict. That is the documented failure mode in
    ``_docs/VERIFICATION.md``: callers must distinguish "no badges" from
    "parser broke" rather than assuming absence means the truth.
    """
    found: dict[str, EarnedBadge] = {}
    chunks = CARD_SPLIT_RE.split(html)[1:]
    for chunk in chunks:
        slug = chunk.split("&", 1)[0].strip()
        if not slug:
            continue
        card = chunk.split("</a>", 1)[0]
        asset = ASSET_RE.search(card)
        if asset is None:
            continue
        badge_slug = asset.group("slug")
        if badge_slug != slug:
            slug = badge_slug
        tier = asset.group("tier").lower()
        label = TIER_LABEL_RE.search(card)
        count = label.group("count").strip() if label else ""
        count = count.removeprefix("x").removeprefix("*").strip()
        if not count.isdigit():
            count = None
        if tier not in TIERS:
            tier = "unknown"
        found[slug] = EarnedBadge(slug=slug, tier=tier, count=count)
    return found


def fetch_profile_html(
    login: str,
    timeout: int = 30,
    attempts: int = 3,
    backoff: float = 1.5,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """GET the public profile page. Read-only, unauthenticated, no token used.

    Retries transient failures because this runs on a weekly CI schedule where a
    single blip would otherwise surface as a red build and train people to ignore
    the check. A 404 is *not* retried: a missing account is a permanent, correct
    answer, and retrying it just delays the error.
    """
    url = f"https://github.com/{login}"
    last_error = ""
    for attempt in range(1, max(1, attempts) + 1):
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_STATUS:
                exc.close()
                raise CatalogError(
                    f"GitHub returned HTTP {exc.code} for {url}"
                    + (" (account does not exist?)" if exc.code == 404 else "")
                ) from exc
            last_error = f"HTTP {exc.code}"
            exc.close()
        except urllib.error.URLError as exc:
            last_error = f"unreachable: {exc.reason}"
            with contextlib.suppress(AttributeError):
                exc.close()
        except TimeoutError:
            last_error = f"timeout after {timeout}s"

        if attempt < attempts:
            sleep(backoff ** (attempt - 1))

    raise CatalogError(
        f"could not fetch {url} after {attempts} attempt(s): {last_error}"
    )


def classify(
    entry: CatalogEntry,
    badge: EarnedBadge | None,
) -> tuple[str, str]:
    """Decide whether a catalog claim matches the live profile."""
    claimed_earned = entry.status.strip().lower() == "earned"
    not_earnable = entry.earnable.strip().lower() in {"false", "no"}

    if entry.status not in VALID_STATUSES or entry.earnable not in {"true", "false"}:
        return (
            "malformed",
            f"meta.yaml has status={entry.status!r} earnable={entry.earnable!r}, "
            f"which is not a documented value",
        )
    if badge is not None and not_earnable:
        return (
            "contradiction",
            f"badge is live but meta.yaml declares earnable: {entry.earnable}",
        )
    if badge is not None and not claimed_earned:
        return (
            "stale-not-earned",
            f"live profile shows '{badge.tier}' but meta.yaml still says '{entry.status}'",
        )
    if badge is None and claimed_earned:
        return (
            "stale-earned",
            "meta.yaml claims 'Earned' but no badge is rendered on the profile",
        )
    if badge is not None:
        suffix = f" (x{badge.count})" if badge.count else ""
        return "earned", f"{badge.tier}{suffix}"
    if not_earnable:
        return "not-earnable", entry.status
    return "not-yet", entry.status


def audit(
    entries: list[CatalogEntry],
    badges: dict[str, EarnedBadge],
) -> list[AuditRow]:
    rows: list[AuditRow] = []
    known = {e.slug for e in entries}
    for entry in entries:
        badge = badges.get(entry.slug)
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
    for slug in sorted(set(badges) - known):
        badge = badges[slug]
        rows.append(
            AuditRow(
                slug=slug,
                claimed_status="(absent from catalog)",
                earnable="(unknown)",
                live_tier=badge.tier,
                live_count=badge.count,
                verdict="uncatalogued",
                detail=f"live badge '{badge.tier}' has no meta.yaml entry",
            )
        )
    return rows


def drift_rows(rows: list[AuditRow]) -> list[AuditRow]:
    return [r for r in rows if r.verdict not in {"earned", "not-yet", "not-earnable"}]


def render_table(rows: list[AuditRow]) -> str:
    headers = ("SLUG", "CLAIMED", "LIVE", "VERDICT", "DETAIL")
    body = [
        (
            r.slug,
            r.claimed_status,
            (r.live_tier or "-") + (f" (x{r.live_count})" if r.live_count else ""),
            r.verdict,
            r.detail,
        )
        for r in rows
    ]
    widths = [
        max(len(headers[i]), max((len(row[i]) for row in body), default=0))
        for i in range(len(headers))
    ]
    lines = [
        "  ".join(headers[i].ljust(widths[i]) for i in range(len(headers))).rstrip(),
        "  ".join("-" * widths[i] for i in range(len(headers))),
    ]
    for row in body:
        lines.append("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))).rstrip())
    return "\n".join(lines)


def count_achievement_cards(html: str) -> int:
    """Count achievement card anchors in the page, independent of asset parsing.

    Used to tell "this account has no badges" apart from "the parser no longer
    understands GitHub's markup". Without this, a CDN or asset-naming change
    makes every badge silently vanish and the audit reports that genuinely
    earned achievements were never earned.
    """
    return len(CARD_SPLIT_RE.findall(html))


def looks_like_profile(html: str) -> bool:
    """Cheap check that we received a rendered profile page and not an error page.

    GitHub serves a 200 for some soft failures (logged-out interstitials, JS
    shells, abuse interstitials). Without this, such a response parses to zero
    badges and the audit would cheerfully report that every earned achievement
    had vanished. ``_docs/VERIFICATION.md`` warns about exactly that failure
    mode, so the warning is enforced here rather than left as advice.
    """
    if "achievement-badge-sidebar" in html:
        return True
    if "tab=achievements" in html:
        return True
    return "user-profile" in html or "js-profile" in html


def validate_login(login: str) -> str:
    """Reject anything that is not a syntactically valid GitHub login.

    Without this, a value containing a control character reaches ``http.client``
    and escapes as an unhandled ``InvalidURL`` traceback rather than a clean
    error. Validating up front also keeps the request URL well-formed.
    """
    if not LOGIN_RE.match(login):
        raise CatalogError(
            f"{login!r} is not a valid GitHub login: expected 1-39 characters "
            "matching [A-Za-z0-9-], not starting or ending with a hyphen"
        )
    return login


def _positive_int(name: str):
    def parse(raw: str) -> int:
        try:
            value = int(raw)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"{name} must be an integer, got {raw!r}") from exc
        if value < 1:
            raise argparse.ArgumentTypeError(f"{name} must be >= 1, got {value}")
        return value

    return parse


def _use_utf8_output() -> None:
    """Make emoji-bearing output safe on legacy Windows consoles (cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(ValueError, OSError):
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _use_utf8_output()
    parser = argparse.ArgumentParser(
        description="Read-only audit of earned GitHub Achievements vs. the local catalog."
    )
    parser.add_argument("--account", default=DEFAULT_ACCOUNT, help="GitHub login to audit")
    parser.add_argument("--catalog", default=ACHIEVEMENTS_DIR, help="path to _achievements/")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    parser.add_argument("--quiet", action="store_true", help="suppress the table; report drift only")
    parser.add_argument("--timeout", type=_positive_int("--timeout"), default=30,
                        help="HTTP timeout in seconds (>= 1)")
    parser.add_argument("--attempts", type=_positive_int("--attempts"), default=3,
                        help="HTTP attempts before giving up (>= 1)")
    args = parser.parse_args(argv)

    try:
        validate_login(args.account)
        entries = parse_catalog(args.catalog)
        html = fetch_profile_html(args.account, timeout=args.timeout, attempts=args.attempts)
    except CatalogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not looks_like_profile(html):
        print(
            f"error: fetched {args.account}'s profile but the response carried no "
            "profile markup. This is a parser/layout problem or an interstitial, "
            "not evidence that the badges disappeared. Refusing to report drift.",
            file=sys.stderr,
        )
        return 1

    cards = count_achievement_cards(html)
    badges = parse_badges(html)

    if cards and not badges:
        print(
            f"error: found {cards} achievement card(s) on the page but extracted 0 "
            "badges. GitHub's badge markup has almost certainly changed (asset host "
            "or naming). Reporting drift now would assert that earned achievements "
            "were never earned, so refusing. Update ASSET_RE in this script.",
            file=sys.stderr,
        )
        return 1

    rows = audit(entries, badges)
    drift = drift_rows(rows)

    if args.json:
        payload = {
            "account": args.account,
            "cards_found": cards,
            "live_badge_count": len(badges),
            "catalog_entry_count": len(entries),
            "drift_count": len(drift),
            "parser_sanity": "ok",
            "rows": [asdict(r) for r in rows],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    elif not args.quiet:
        print(f"Account: {args.account}")
        print(
            f"Cards: {cards}   Live badges: {len(badges)}   "
            f"Catalog entries: {len(entries)}"
        )
        print()
        print(render_table(rows))
        print()

    # With --json, stdout must stay pure JSON so `| jq` works, so the human
    # summary is diverted to stderr.
    summary = sys.stderr if args.json else sys.stdout
    if drift:
        print(
            f"DRIFT: {len(drift)} catalog entr"
            f"{'y' if len(drift) == 1 else 'ies'} disagree with the live profile",
            file=summary,
        )
        for row in drift:
            print(f"  - {row.slug}: {row.detail}", file=summary)
        return 2

    print("OK: catalog matches the live profile", file=summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
