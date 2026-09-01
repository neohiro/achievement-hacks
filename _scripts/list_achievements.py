#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""list_achievements.py — Canonical inventory of all known GitHub Achievements.

Reads _achievements/*/meta.yaml and prints a markdown table.
Fails with a non-zero exit code if any meta.yaml fails to parse.

Usage:
    python _scripts/list_achievements.py
    python _scripts/list_achievements.py --format table   # default: markdown table
    python _scripts/list_achievements.py --format json  # JSON snapshot
    python _scripts/list_achievements.py --check        # validate only, no output
"""
import argparse
import json
import sys
from pathlib import Path

# Ensure stdout can print emoji on Windows (default cp1252 cannot).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
ACHIEVEMENTS_DIR = REPO_ROOT / "_achievements"


def load_meta(slug_dir: Path) -> dict:
    meta_path = slug_dir / "meta.yaml"
    if not meta_path.exists():
        raise ValueError(f"{meta_path} exists but has no meta.yaml")
    try:
        import yaml
        with open(meta_path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"{meta_path}: invalid YAML — {exc}")


def collect_slug_dirs(base: Path):
    """Walk one level deep: recurse into _deprecated/ and _highlights/ as
    category containers, treat immediate children of _achievements/ as top-level
    achievement folders. Returns leaf dirs that contain meta.yaml."""
    leaves = []
    for entry in base.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name.startswith("_"):
            # Category container — recurse one level
            for sub in entry.iterdir():
                if sub.is_dir() and (sub / "meta.yaml").exists():
                    leaves.append(sub)
        else:
            if (entry / "meta.yaml").exists():
                leaves.append(entry)
    return leaves


def slug_sort_key(path: Path) -> str:
    parts = path.parts
    prefix = 2 if any(p.startswith("_") for p in parts[:-1]) else 0
    meta = {}
    try:
        meta = load_meta(path)
    except ValueError:
        pass
    tiers = len(meta.get("tiers", []))
    return f"{prefix}:{tiers:02d}:{path.name}"


def main():
    parser = argparse.ArgumentParser(
        description="List all achievements from meta.yaml files in _achievements/."
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate meta.yaml files without producing output.",
    )
    args = parser.parse_args()

    slug_dirs = collect_slug_dirs(ACHIEVEMENTS_DIR)

    # Sort: _deprecated/_highlights last, then by tier count desc, then slug
    slug_dirs.sort(key=slug_sort_key)

    rows = []
    errors = []
    for slug_dir in slug_dirs:
        try:
            data = load_meta(slug_dir)
            rows.append(data)
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.check:
        print(f"OK: {len(rows)} achievements validated, no errors.", file=sys.stderr)
        return

    if args.format == "json":
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return

    # Markdown table
    print("| # | Slug | Name | Emoji | Status | Earnable | Tiers |")
    print("|---|---|---|---|---|---|---|")
    for i, data in enumerate(rows, 1):
        slug = data.get("slug", "?")
        name = data.get("name", "?")
        emoji = data.get("emoji", "")
        status = data.get("status", "?")
        earnable = "Yes" if data.get("earnable", True) else "No"
        tier_count = len(data.get("tiers", []))
        tier_range = f"{tier_count}"
        print(f"| {i} | `{slug}` | {name} | {emoji} | {status} | {earnable} | {tier_range} |")


if __name__ == "__main__":
    main()
