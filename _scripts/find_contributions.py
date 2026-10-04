#!/usr/bin/env python3
"""find_contributions.py - surface genuine places to make a real first contribution.

Open Sourcerer is the only remaining badge that can be earned by ordinary work:
get a commit merged into a public repository you do not own. The hard part is
not the badge, it is finding a project where a newcomer is genuinely wanted and
where the maintainer will actually review a PR.

This is that finder. It is read-only: it searches public issues carrying
newcomer-friendly labels and prints candidates. It does not open issues,
comment, react, or fork anything.

What it deliberately does NOT do is generate a contribution for you. There is no
script here that produces a PR a maintainer did not ask for, because the badge
is not the point -- the merged contribution is.

Usage:
    python find_contributions.py                       # default label set
    python find_contributions.py --limit 30
    python find_contributions.py --label "help wanted"
    python find_contributions.py --json
    python find_contributions.py --account neohiro

Exit codes:
    0  candidates found
    1  usage, auth, or network error
    2  no candidates matched

Requires: Python 3.10+ stdlib plus the authenticated `gh` CLI.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_ACCOUNT = "neohiro"

# Labels that signal a maintainer wants outside help. Ordered by how reliably
# they lead to a merged PR rather than a stale issue nobody will read.
DEFAULT_LABELS = (
    "good first issue",
    "help wanted",
    "first-timers-only",
)

GH_TIMEOUT = 120


class FinderError(RuntimeError):
    """Raised when gh is unusable or returns something we cannot parse."""


def _use_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(ValueError, OSError):
            reconfigure(encoding="utf-8", errors="replace")


def run_gh(args: list[str]) -> str:
    """Run a gh subcommand read-only and return stdout.

    ``check=False`` deliberately: we want gh's own stderr on failure rather than
    a traceback, and we classify the error ourselves below.
    """
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=GH_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise FinderError(
            "'gh' CLI not found. Install it from https://cli.github.com and run "
            "'gh auth login'."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise FinderError(f"gh timed out after {GH_TIMEOUT}s: {' '.join(args)}") from exc

    if result.returncode != 0:
        detail = (result.stderr or "").strip() or f"exit {result.returncode}"
        raise FinderError(f"gh {' '.join(args[:2])} failed: {detail[:300]}")
    return result.stdout


def search_issues(label: str, limit: int) -> list[dict]:
    """Search public issues carrying ``label``. Read-only."""
    out = run_gh(
        [
            "search", "issues",
            "--label", label,
            "--state", "open",
            "--limit", str(limit),
            "--json", "url,title,repository,updatedAt,commentsCount,labels",
            "--sort", "updated",
            "--order", "desc",
        ]
    )
    try:
        data = json.loads(out or "[]")
    except json.JSONDecodeError as exc:
        raise FinderError(f"could not parse gh output for label {label!r}") from exc
    if not isinstance(data, list):
        raise FinderError(f"unexpected gh payload for label {label!r}")
    return [item for item in data if isinstance(item, dict)]


def repo_name(item: dict) -> str:
    """Full ``owner/name`` for a search result.

    Tolerates a missing or non-dict ``repository`` so a gh schema change degrades
    to a blank cell rather than an AttributeError mid-list.
    """
    repo = item.get("repository")
    if not isinstance(repo, dict):
        return ""
    return str(repo.get("nameWithOwner") or "")


def owner_of(item: dict) -> str:
    """The account that owns the repository, lowercased for comparison."""
    return repo_name(item).split("/")[0].lower()


def collect(labels: tuple[str, ...], limit: int) -> list[dict]:
    """Gather candidates across labels, de-duplicated by issue URL.

    Ordering is deliberate and uses two stable passes:

    1. Most recently active first, so stale issues do not lead the list.
    2. Then fewest comments first, so unclaimed issues win ties.

    A single ascending sort on ``(comments, updatedAt)`` gets this wrong: it
    surfaces the *stalest* issues first, which is the opposite of what makes a
    good first contribution land.
    """
    seen: dict[str, dict] = {}
    for label in labels:
        for item in search_issues(label, limit):
            url = item.get("url")
            if not url or url in seen:
                continue
            item = dict(item)
            item["matched_label"] = label
            seen[url] = item

    items = list(seen.values())
    items.sort(key=lambda i: str(i.get("updatedAt") or ""), reverse=True)
    items.sort(key=lambda i: i.get("commentsCount") or 0)
    return items


def filter_out_own_repos(
    items: list[dict], account: str, owned: set[str]
) -> list[dict]:
    """Drop candidates on repositories the account can already push to.

    Open Sourcerer needs a repo you do *not* own, and a PR to a repo you own is
    Pull Shark, which we already hold.
    """
    account = account.lower()
    out = []
    for item in items:
        full = repo_name(item)
        if owner_of(item) == account or full.lower() in owned:
            continue
        out.append(item)
    return out


def load_owned_repos() -> set[str]:
    """Repositories the account can push to, lowercased full names."""
    try:
        out = run_gh(
            [
                "repo", "list", "--limit", "200", "--json", "nameWithOwner",
                "--source", "member,owner",
            ]
        )
        data = json.loads(out or "[]")
    except (FinderError, json.JSONDecodeError):
        return set()
    return {
        str(r.get("nameWithOwner", "")).lower()
        for r in data
        if isinstance(r, dict) and r.get("nameWithOwner")
    }


def render(items: list[dict]) -> str:
    lines = []
    for item in items:
        repo = repo_name(item) or "?"
        comments = item.get("commentsCount")
        freshness = f"comments={comments}" if comments is not None else ""
        lines.append(f"  {repo}")
        lines.append(f"    {item.get('title', '')}")
        lines.append(
            f"    {item.get('url', '')}   [{item.get('matched_label', '')}] {freshness}"
        )
    return "\n".join(lines)


def cap_per_repo(items: list[dict], per_repo: int) -> list[dict]:
    """Limit how many candidates any single repository may contribute.

    Without this, label-sorted results are dominated by content farms: a repo
    with 31,000 open `good first issue` entries fills the whole list and crowds
    out the handful of real projects. A newcomer wants breadth of projects, not
    the 25th anime quote.
    """
    if per_repo < 1:
        return items
    counts: dict[str, int] = {}
    kept: list[dict] = []
    for item in items:
        repo = repo_name(item)
        seen = counts.get(repo, 0)
        if seen >= per_repo:
            continue
        counts[repo] = seen + 1
        kept.append(item)
    return kept


def main(argv: list[str] | None = None) -> int:
    _use_utf8_output()
    parser = argparse.ArgumentParser(
        description="Find real places to contribute (read-only; opens nothing)."
    )
    parser.add_argument(
        "--label",
        action="append",
        dest="labels",
        help="search label; repeatable. Defaults to a newcomer-friendly set.",
    )
    parser.add_argument("--limit", type=int, default=25, help="results per label")
    parser.add_argument(
        "--per-repo",
        type=int,
        default=2,
        help="max candidates from any one repository (0 = unlimited)",
    )
    parser.add_argument("--account", default=DEFAULT_ACCOUNT, help="login to exclude own repos")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--include-own", action="store_true", help="do not filter repositories you own"
    )
    args = parser.parse_args(argv)

    if args.limit < 1:
        print("error: --limit must be >= 1", file=sys.stderr)
        return 1

    labels = tuple(args.labels) if args.labels else DEFAULT_LABELS

    try:
        items = collect(labels, args.limit)
        if not args.include_own:
            items = filter_out_own_repos(items, args.account, load_owned_repos())
        items = cap_per_repo(items, args.per_repo)
    except FinderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
        return 0 if items else 2

    if not items:
        print("No candidates matched. Try --label with another, or a larger --limit.")
        return 2

    print(f"{len(items)} candidate(s) across {len(labels)} label(s).")
    print()
    print(render(items))
    print()
    print("Before opening anything:")
    print("  1. Read CONTRIBUTING.md. Unlabelled-obedience PRs get closed.")
    print("  2. Check the issue is still open and nobody has already claimed it.")
    print("  3. Match the project's style; run its tests.")
    print("  4. One focused change per PR. Do not reformat unrelated lines.")
    print("  5. Say what you tested. Maintainers merge PRs they can verify.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
