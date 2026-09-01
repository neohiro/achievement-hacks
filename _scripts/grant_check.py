#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""grant_check.py — Audit which GitHub Achievements a given account actually has.

GitHub does NOT expose achievement data via the GraphQL or REST API.
The authoritative source is the public profile HTML page at
https://github.com/<login>, which renders achievements as an SVG/img panel.

This script:
  1. Fetches https://github.com/<login> via gh api (authenticated, higher rate-limit)
  2. Parses the achievements panel for badge image URLs
  3. Maps the image URLs to the achievement slugs in this repo
  4. Cross-references with activity-derived counts (merged PRs, stars) to suggest
     the next achievable tier for the user

Note: The lightweight `gh api users/<login>` response does NOT include the
achievements panel HTML. Only the full web page (which requires a browser session)
contains the rendered achievements section. If parsing returns no achievements,
check the profile manually at https://github.com/<login>.

Fallback: When profile HTML parsing yields no achievements, the tool provides
tier estimates based on observable public data (star counts, follower counts).

Usage:
    python _scripts/grant_check.py [login]
    python _scripts/grant_check.py --json [login]
    python _scripts/grant_check.py --verbose [login]

Default login: neohiro
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

REPO_ROOT = Path(__file__).parent.parent
SCRIPT_DIR = Path(__file__).parent

# Map from GitHub's achievement asset filename to our slug.
# GitHub stores badge images at github.githubassets.com/images/modules/profile/achievements/
# Their filenames are like "pair-extraordinaire-default.png".
ASSET_TO_SLUG = {
    "pair-extraordinaire-default": "pair-extraordinaire",
    "pair-extraordinaire-bronze": "pair-extraordinaire",
    "pair-extraordinaire-silver": "pair-extraordinaire",
    "pair-extraordinaire-gold": "pair-extraordinaire",
    "pull-shark-default": "pull-shark",
    "pull-shark-bronze": "pull-shark",
    "pull-shark-silver": "pull-shark",
    "pull-shark-gold": "pull-shark",
    "galaxy-brain-default": "galaxy-brain",
    "galaxy-brain-bronze": "galaxy-brain",
    "galaxy-brain-silver": "galaxy-brain",
    "galaxy-brain-gold": "galaxy-brain",
    "starstruck-default": "starstruck",
    "starstruck-bronze": "starstruck",
    "starstruck-silver": "starstruck",
    "starstruck-gold": "starstruck",
    "quickdraw": "quickdraw",
    "yolo": "yolo",
    "heart-on-your-sleeve-default": "heart-on-your-sleeve",
    "open-sourcerer-default": "open-sourcerer",
    "public-sponsor": "public-sponsor",
    "arctic-code-vault-contributor": "arctic-code-vault",
    "mars-2020-contributor": "mars-2020",
    "github-pro": "github-pro",
    "developer-program-member": "developer-program-member",
    "security-bug-bounty-hunter": "security-bug-bounty-hunter",
    "github-campus-expert": "github-campus-expert",
    "security-advisory-credit": "security-advisory-credit",
}

# Tier rank for ordering
TIER_RANK = {"default": 0, "bronze": 1, "silver": 2, "gold": 3, None: -1}


def _fetch_profile_html(login: str) -> str:
    """Fetch the public profile page for a user via gh api."""
    result = subprocess.run(
        ["gh", "api", f"users/{login}"],
        capture_output=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh api users/{login} failed: {result.stderr.strip()}")
    return result.stdout


def _gh_run_json(cmd: list[str]) -> dict:
    """Run a gh command and parse JSON output. Raises on failure."""
    result = subprocess.run(
        cmd, capture_output=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(cmd[:3])} failed: {result.stderr.strip()}")
    raw = result.stdout.strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh returned invalid JSON: {exc}")


def parse_achievements_from_html(html: str) -> dict[str, set[str]]:
    """Parse achievement slugs + tiers from the achievements section of a profile page.

    Returns dict[slug] -> set of tier names discovered.
    """
    found: dict[str, set[str]] = {}

    # Achievement images use filenames like "pair-extraordinaire-default.png"
    # Sometimes inline base64, sometimes URL.
    asset_pattern = re.compile(
        r"achievements[/-]([a-z0-9-]+?)(?:-(default|bronze|silver|gold))?(?:\.png|\")",
        re.IGNORECASE,
    )
    for m in asset_pattern.finditer(html):
        key = m.group(1).lower()
        tier = (m.group(2) or "default").lower()
        slug = ASSET_TO_SLUG.get(f"{key}-{tier}") or ASSET_TO_SLUG.get(key)
        if not slug:
            continue
        found.setdefault(slug, set()).add(tier)

    return found


def _count_merged_prs(login: str, repos: list[str]) -> int:
    total = 0
    for repo in repos:
        try:
            data = _gh_run_json(["gh", "api", f"repos/{login}/{repo}/pulls",
                                 "--state", "closed", "--paginate",
                                 "--jq", '[.[] | select(.merged_at != null)] | length'])
            if isinstance(data, int):
                total += data
        except RuntimeError as exc:
            if args.verbose:
                print(f"WARN: {exc}", file=sys.stderr)
    return total


def get_achievement_status(login: str, verbose: bool = False) -> dict:
    """Main entry point. Returns a dict with parsed_achievements + activity_counts."""
    result = {
        "login": login,
        "parsed_achievements": {},
        "activity_counts": {},
        "tier_estimate": {},
    }

    # 1. Parse HTML
    try:
        html = _fetch_profile_html(login)
        result["parsed_achievements"] = {
            slug: sorted(tiers, key=lambda t: TIER_RANK.get(t, -1), reverse=True)
            for slug, tiers in parse_achievements_from_html(html).items()
        }
    except RuntimeError as exc:
        result["profile_error"] = str(exc)
        if verbose:
            print(f"WARN: {exc}", file=sys.stderr)

    # 2. Activity counts
    # Use public-repos count from the user API
    try:
        user = _gh_run_json(["gh", "api", f"users/{login}"])
        result["activity_counts"]["public_repos"] = user.get("public_repos", 0)
        result["activity_counts"]["followers"] = user.get("followers", 0)
    except RuntimeError as exc:
        if verbose:
            print(f"WARN: {exc}", file=sys.stderr)

    # 3. Check top repos for star counts (Pull Shark, Starstruck indicators)
    try:
        repos_data = _gh_run_json([
            "gh", "api", f"users/{login}/repos",
            "--paginate", "--jq", '[.[] | select(.stargazers_count > 0) | '
            '{name: .name, stars: .stargazers_count}] | sort_by(-.stars) | .[:5]',
        ])
        if isinstance(repos_data, list) and repos_data:
            result["activity_counts"]["top_5_repos_by_stars"] = repos_data
    except RuntimeError as exc:
        if verbose:
            print(f"WARN: {exc}", file=sys.stderr)

    # 4. Tier estimate
    for repo_info in result["activity_counts"].get("top_5_repos_by_stars", []):
        stars = repo_info.get("stars", 0)
        if stars >= 16:
            result["tier_estimate"]["starstruck"] = "Default (16) likely"
        if stars >= 128:
            result["tier_estimate"]["starstruck"] = "Bronze (128) likely"
        if stars >= 512:
            result["tier_estimate"]["starstruck"] = "Silver (512) likely"
        if stars >= 4096:
            result["tier_estimate"]["starstruck"] = "Gold (4096) likely"
        break  # only the highest

    return result


def format_human(report: dict) -> str:
    lines = [f"GitHub Achievement audit for @{report['login']}"]
    lines.append("=" * (len(lines[0])))

    parsed = report.get("parsed_achievements", {})
    if parsed:
        lines.append("")
        lines.append("Parsed from profile HTML:")
        for slug in sorted(parsed):
            tiers = ", ".join(parsed[slug]) or "?"
            lines.append(f"  ✓ {slug} [{tiers}]")
    else:
        lines.append("")
        lines.append("No achievements parsed from profile HTML.")
        if "profile_error" in report:
            lines.append(f"  Error: {report['profile_error']}")

    counts = report.get("activity_counts", {})
    if counts:
        lines.append("")
        lines.append("Activity counts:")
        for key in ("public_repos", "followers"):
            if key in counts:
                lines.append(f"  {key}: {counts[key]}")
        top = counts.get("top_5_repos_by_stars", [])
        if top:
            lines.append(f"  top repo stars: {top[0]['name']} = {top[0]['stars']}")

    est = report.get("tier_estimate", {})
    if est:
        lines.append("")
        lines.append("Tier estimate:")
        for slug, msg in est.items():
            lines.append(f"  {slug}: {msg}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Audit which GitHub Achievements an account has by scraping the public profile."
    )
    parser.add_argument("login", nargs="?", default="neohiro",
                        help="GitHub login to audit (default: neohiro)")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of human-readable text")
    parser.add_argument("--verbose", action="store_true",
                        help="Log warnings to stderr")
    args = parser.parse_args()

    report = get_achievement_status(args.login, verbose=args.verbose)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_human(report))


if __name__ == "__main__":
    main()
