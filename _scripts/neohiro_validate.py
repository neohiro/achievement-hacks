#!/usr/bin/env python3
"""neohiro_validate.py — unified validation CLI for achievement-hacks.

Runs the same checks the test_*.py suites use, in one place:
  - ruff linting on every .py file in _scripts/
  - list_achievements.py --validate-schema --check  (strict JSON Schema)
  - test_file_vuln_issues.py (41 unit tests)
  - file_vuln_issues.py --sync --dry-run  (idempotency check)
  - grant_check.py --json neohiro  (profile audit)
  - file/folder structure under _achievements/, _deprecated/, _highlights/

Output: human-readable by default; --json for machine consumption.
Exit code: 0 = all OK, 1 = findings, 2 = tool missing or bad args.

Usage:
    python _scripts/neohiro_validate.py
    python _scripts/neohiro_validate.py --json
    python _scripts/neohiro_validate.py --only ruff,schema,sync
    python _scripts/neohiro_validate.py --skip grant_check
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from contextlib import suppress
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "_scripts"

ALL_CHECKS = {
    "ruff", "schema", "unit", "sync", "grant_check", "structure",
}
DEFAULT_CHECKS = {"ruff", "schema", "unit", "sync", "structure"}

# Reasonable per-check timeout (seconds). Grant check requires network; bumped.
DEFAULT_TIMEOUT = 30
GRANT_TIMEOUT = 60


def _run_ruff() -> dict:
    """Run ruff on _scripts/; return a check-result dict."""
    proc = subprocess.run(
        [sys.executable, "-m", "ruff", "check", str(SCRIPTS_DIR)],
        capture_output=True, encoding="utf-8", errors="replace", timeout=DEFAULT_TIMEOUT,
    )
    findings: list[str] = []
    if proc.returncode != 0 and proc.stdout.strip():
        # Ruff format: "All checks passed!" or "<file>:<line>:<col> <code> <msg>"
        for line in proc.stdout.splitlines():
            line = line.rstrip()
            if line and "All checks passed!" not in line:
                findings.append(line)
    return {
        "check": "ruff",
        "status": "ok" if proc.returncode == 0 else "fail",
        "returncode": proc.returncode,
        "findings": findings,
        "summary": f"{len(findings)} ruff issue(s)" if findings else "0 ruff issues",
    }


def _run_schema() -> dict:
    """Run list_achievements.py --validate-schema --check."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "list_achievements.py"),
         "--validate-schema", "--check"],
        capture_output=True, encoding="utf-8", errors="replace", timeout=DEFAULT_TIMEOUT,
    )
    ok = proc.returncode == 0 and "OK" in proc.stderr
    return {
        "check": "schema",
        "status": "ok" if ok else "fail",
        "returncode": proc.returncode,
        "stderr_tail": proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "",
        "summary": proc.stderr.strip().splitlines()[-1] if ok else "schema validation failed",
    }


def _run_unit() -> dict:
    """Run the unit test suite."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "test_file_vuln_issues.py")],
        capture_output=True, encoding="utf-8", errors="replace", timeout=DEFAULT_TIMEOUT,
    )
    # Parse "Ran 41 tests in 0.3s\nOK" or "FAILED (errors=1)"
    lines = [ln for ln in proc.stderr.splitlines() if ln.startswith(("Ran ", "OK", "FAILED"))]
    summary = lines[-1] if lines else (lines[0] if lines else "no output")
    return {
        "check": "unit",
        "status": "ok" if proc.returncode == 0 else "fail",
        "returncode": proc.returncode,
        "summary": summary,
    }


def _run_sync() -> dict:
    """Run file_vuln_issues.py --sync --dry-run --format summary."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "file_vuln_issues.py"),
         "--sync", "--dry-run", "--format", "summary"],
        capture_output=True, encoding="utf-8", errors="replace", timeout=DEFAULT_TIMEOUT,
    )
    failed_match = "Failed=0" in proc.stderr
    ok = proc.returncode == 0 and failed_match
    return {
        "check": "sync",
        "status": "ok" if ok else "fail",
        "returncode": proc.returncode,
        "summary": (proc.stderr.strip().splitlines()[-1]
                    if proc.stderr.strip() else "no output"),
    }


def _run_grant_check() -> dict:
    """Run grant_check.py --json neohiro (requires network + gh auth)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "grant_check.py"),
         "--json", "neohiro"],
        capture_output=True, encoding="utf-8", errors="replace", timeout=GRANT_TIMEOUT,
    )
    parsed = {}
    with suppress(json.JSONDecodeError):
        parsed = json.loads(proc.stdout)
    return {
        "check": "grant_check",
        "status": "ok" if proc.returncode == 0 else "fail",
        "returncode": proc.returncode,
        "login": parsed.get("login"),
        "achievements_parsed": len(parsed.get("parsed_achievements", {})),
        "public_repos": parsed.get("activity_counts", {}).get("public_repos"),
        "summary": f"parsed {len(parsed.get('parsed_achievements', {}))} achievements"
                   f" for {parsed.get('login', '?')}",
    }


def _run_structure() -> dict:
    """Verify every achievement folder has meta.yaml + README.md, and required
    files at the repo root."""
    findings: list[str] = []
    required_root = ["README.md", "SECURITY.md", "STATUS.md",
                     "_docs/meta.schema.json", "_docs/ACHIEVEMENT_INDEX.md"]
    for path in required_root:
        if not (REPO_ROOT / path).exists():
            findings.append(f"missing required file: {path}")

    achievements_dir = REPO_ROOT / "_achievements"
    for entry in achievements_dir.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        sub_iter = [entry]
        if entry.name.startswith("_"):
            sub_iter = list(entry.iterdir())
        for sub in sub_iter:
            if not sub.is_dir():
                continue
            if not (sub / "meta.yaml").exists():
                findings.append(f"missing meta.yaml: {sub.relative_to(REPO_ROOT)}")
            if not (sub / "README.md").exists():
                findings.append(f"missing README.md: {sub.relative_to(REPO_ROOT)}")

    return {
        "check": "structure",
        "status": "ok" if not findings else "fail",
        "findings": findings,
        "summary": f"{len(findings)} structural finding(s)" if findings
                   else "structure OK",
    }


CHECKS = {
    "ruff": _run_ruff,
    "schema": _run_schema,
    "unit": _run_unit,
    "sync": _run_sync,
    "grant_check": _run_grant_check,
    "structure": _run_structure,
}


def _format_human(results: list[dict]) -> str:
    lines: list[str] = ["neohiro_validate.py — achievement-hacks", "=" * 38, ""]
    for r in results:
        status = "[ OK ]" if r["status"] == "ok" else "[FAIL]"
        lines.append(f"{status} {r['check']:14s} {r.get('summary', '')}")
        for f in r.get("findings", []):
            lines.append(f"        - {f}")
    failed = sum(1 for r in results if r["status"] != "ok")
    lines.append("")
    lines.append(f"Summary: {len(results) - failed} OK, {failed} failed")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Unified validation CLI for achievement-hacks."
    )
    parser.add_argument(
        "--only", default="",
        help=f"Comma-separated check names (one of {sorted(ALL_CHECKS)}). "
             f"Default: {','.join(sorted(DEFAULT_CHECKS))}",
    )
    parser.add_argument(
        "--skip", default="",
        help="Comma-separated check names to skip.",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output JSON instead of human-readable text.",
    )
    args = parser.parse_args()

    selected = set(args.only.split(",")) if args.only else set(DEFAULT_CHECKS)
    skipped = set(args.skip.split(",")) if args.skip else set()
    unknown = (selected | skipped) - ALL_CHECKS
    if unknown:
        print(f"ERROR: unknown check(s): {sorted(unknown)}", file=sys.stderr)
        return 2

    selected -= skipped
    if not selected:
        print("ERROR: no checks selected", file=sys.stderr)
        return 2

    results: list[dict] = []
    for name in sorted(selected):
        runner = CHECKS.get(name)
        if runner is None:
            continue
        try:
            results.append(runner())
        except subprocess.TimeoutExpired:
            results.append({
                "check": name, "status": "fail",
                "summary": "TIMEOUT", "returncode": -1,
            })
        except FileNotFoundError as exc:
            results.append({
                "check": name, "status": "fail",
                "summary": f"missing tool: {exc}", "returncode": -1,
            })

    if args.json:
        print(json.dumps({"results": results,
                          "summary": {
                              "total": len(results),
                              "ok": sum(1 for r in results if r["status"] == "ok"),
                              "failed": sum(1 for r in results if r["status"] != "ok"),
                          }}, indent=2, ensure_ascii=False))
    else:
        print(_format_human(results))

    return 0 if all(r["status"] == "ok" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
