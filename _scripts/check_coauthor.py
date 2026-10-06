#!/usr/bin/env python3
"""check_coauthor.py - audit Co-authored-by trailers on recent commits.

Pair Extraordinaire is awarded for a commit you genuinely co-authored. The
mechanism is a `Co-authored-by:` trailer, and GitHub's attribution is strict: if
the trailer is malformed the commit still lands, it just is not attributed to
anyone. That failure is silent, which is exactly why people reach for the
forged-trailer "solution" instead of fixing the address.

This lints the trailers so a real collaboration is not lost to a typo.

It does not create commits, invent co-authors, or sign anything. It reads.

Usage:
    python check_coauthor.py                     # audit HEAD commit
    python check_coauthor.py --last 10          # audit the last 10 commits
    python check_coauthor.py --branch main      # audit every commit on a branch
    python check_coauthor.py --json

Exit codes:
    0  every trailer present is well formed
    1  usage or git error
    2  at least one malformed trailer

Requires: Python 3.10+ stdlib and git.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import re
import subprocess
import sys

GIT_TIMEOUT = 60

# GitHub requires exactly: "Name <email>" where the address is the account's
# real address or its no-reply form. A commit trailer without a valid address is
# ignored by GitHub for attribution purposes.
TRAILER_RE = re.compile(r"^Co-authored-by:\s*(?P<name>[^<]*?)\s*<(?P<email>[^>]*)>\s*$")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

FIELD_SEP = "\x1f"
RECORD_SEP = "\x1e"


class GitError(RuntimeError):
    """Raised when git is unavailable or returns an error."""


def _use_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(ValueError, OSError):
            reconfigure(encoding="utf-8", errors="replace")


def run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise GitError("git not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"git timed out after {GIT_TIMEOUT}s") from exc
    if result.returncode != 0:
        raise GitError((result.stderr or "").strip() or f"git {' '.join(args)} failed")
    return result.stdout


def commits_to_check(last: int | None, branch: str | None) -> list[dict]:
    """Resolve which commits to audit, with subject and message in one call.

    A single ``git log`` with record/field separators replaces two subprocess
    spawns per commit, so ``--last 100`` costs 1 call instead of ~201.
    """
    if branch:
        spec = f"origin/{branch}..HEAD"
    elif last is not None:
        spec = f"-{last}"
    else:
        spec = "-1"

    # The record separator must terminate each commit, not sit between the
    # subject and the body, otherwise every commit splits into two chunks and the
    # second is misread as a commit whose "sha" is the previous subject line.
    out = run_git(
        ["log", spec, f"--format=%H{FIELD_SEP}%s{FIELD_SEP}%B{RECORD_SEP}"]
    )
    records = []
    for chunk in out.split(RECORD_SEP):
        if not chunk.strip():
            continue
        sha, _, remainder = chunk.partition(FIELD_SEP)
        subject, _, body = remainder.partition(FIELD_SEP)
        records.append({"sha": sha.strip(), "subject": subject.strip(), "body": body})
    return records


def commit_trailers(body: str) -> list[str]:
    """Trailer lines from a raw commit message, ignoring comment lines.

    ``git log %B`` can carry the scissors line and a commented diff, so comment
    lines are dropped before scanning for trailers.
    """
    kept = [
        line.strip()
        for line in body.split("\n")
        if not line.strip().startswith("#")
    ]
    return [line for line in kept if line.lower().startswith("co-authored-by:")]


def check_trailer(line: str) -> tuple[bool, str]:
    """Return (ok, reason). Reason is empty when the trailer is well formed."""
    match = TRAILER_RE.match(line)
    if match is None:
        return False, "expected exactly 'Co-authored-by: Name <email@example.com>'"
    name = match.group("name")
    email = match.group("email")
    if not name:
        return False, "missing co-author name"
    if not email:
        return False, "missing co-author email; GitHub will not attribute this"
    if not EMAIL_RE.match(email):
        return False, f"email {email!r} is not a valid address"
    return True, ""


def audit(last: int | None, branch: str | None) -> list[dict]:
    findings: list[dict] = []
    for record in commits_to_check(last, branch):
        trailers = commit_trailers(record["body"])
        findings.append(
            {
                "sha": record["sha"][:12],
                "subject": record["subject"],
                "trailers": trailers,
                "problems": [
                    reason
                    for line in trailers
                    for ok, reason in [check_trailer(line)]
                    if not ok
                ],
            }
        )
    return findings


def render(findings: list[dict]) -> str:
    lines = []
    for item in findings:
        mark = "FAIL" if item["problems"] else "ok  "
        lines.append(f"  [{mark}] {item['sha']}  {item['subject']}")
        for trailer in item["trailers"]:
            lines.append(f"           {trailer}")
        for problem in item["problems"]:
            lines.append(f"           -> {problem}")
        if not item["trailers"]:
            lines.append("           (no co-author trailer)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    _use_utf8_output()
    parser = argparse.ArgumentParser(
        description="Validate Co-authored-by trailers so real co-authorship is not lost to a typo."
    )
    parser.add_argument("--last", type=int, default=None, help="audit the last N commits")
    parser.add_argument("--branch", default=None, help="audit commits on this branch vs origin")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    if args.last is not None and args.last < 1:
        print("error: --last must be >= 1", file=sys.stderr)
        return 1

    try:
        findings = audit(args.last, args.branch)
    except GitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    bad = [f for f in findings if f["problems"]]

    if args.json:
        print(json.dumps({"commits": findings, "malformed": len(bad)},
                         indent=2, ensure_ascii=False))
    else:
        print(render(findings))
        print()
        if bad:
            print(f"{len(bad)} commit(s) have a trailer GitHub will not attribute.")
        else:
            print("All trailers well formed.")
            if not any(f["trailers"] for f in findings):
                print("No co-author trailers found; Pair Extraordinaire needs at least one.")

    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
