#!/usr/bin/env python3
"""submit_contribution.py - open a well-formed pull request for a change you made.

Open Sourcerer is earned by having a commit merged into a public repository you do
not own. That is a real contribution, so the work is yours; automating it would
just be spam. What this script automates is the *mechanics* around your work, the
part that is tedious and easy to get wrong:

  - confirming the branch actually carries commits over the base
  - refusing to open a PR with no commits, which silently creates an empty PR
  - building a body that states what was tested and links the issue
  - wiring `Closes #N` so the issue closes on merge

It does not write code, generate a diff, or decide what to change. If you have
not made the change yet, this has nothing to do.

Usage:
    python submit_contribution.py --title "Fix typo in README" --repo owner/name
    python submit_contribution.py --title "..." --repo owner/name --body-file notes.md
    python submit_contribution.py --title "..." --repo owner/name --closes 42
    python submit_contribution.py --title "..." --repo owner/name --dry-run

Exit codes:
    0  pull request opened (or would be, with --dry-run)
    1  usage, git, or gh error
    2  pre-flight check failed (nothing was opened)
"""
from __future__ import annotations

import argparse
import contextlib
import re
import subprocess
import sys

GIT_TIMEOUT = 60
GH_TIMEOUT = 180


REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
DOT_SEGMENTS = frozenset({".", ".."})


def validate_repo(repo: str) -> str:
    """GitHub repository slugs are exactly owner/name.

    A loose "contains a slash" check let `a/b/c` through, which then flowed into
    `gh --repo` and failed late and confusingly. Traversal segments are rejected
    explicitly: they match the character class, and a value shaped like a path
    should never reach a CLI that takes a repository slug.
    """
    if not REPO_RE.match(repo):
        raise ToolError(
            f"--repo must look like owner/name (letters, digits, '.', '_', '-'), "
            f"got {repo!r}"
        )
    if any(part in DOT_SEGMENTS for part in repo.split("/")):
        raise ToolError(f"--repo must not contain '.' or '..' segments, got {repo!r}")
    return repo


class PreflightError(RuntimeError):
    """A condition that means we should not open a pull request."""


class ToolError(RuntimeError):
    """git or gh was unusable."""


def _use_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(ValueError, OSError):
            reconfigure(encoding="utf-8", errors="replace")


def _run(cmd: list[str], timeout: int) -> str:
    tool = cmd[0]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise ToolError(f"{tool} not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"{tool} timed out after {timeout}s") from exc
    if result.returncode != 0:
        raise ToolError((result.stderr or "").strip() or f"{tool} failed")
    return result.stdout


def git(args: list[str]) -> str:
    return _run(["git", *args], GIT_TIMEOUT)


def gh(args: list[str]) -> str:
    return _run(["gh", *args], GH_TIMEOUT)


def current_branch() -> str:
    try:
        return git(["rev-parse", "--abbrev-ref", "HEAD"]).strip()
    except ToolError as exc:
        raise PreflightError(f"not a git repository, or git failed: {exc}") from exc


def commits_ahead(base: str) -> list[str]:
    """Commit subjects on this branch that are not on the base ref."""
    try:
        out = git(["log", "--format=%h %s", f"origin/{base}..HEAD"])
    except ToolError:
        try:
            out = git(["log", "--format=%h %s", f"{base}..HEAD"])
        except ToolError as exc:
            raise PreflightError(
                f"cannot compare against base {base!r}; fetch first "
                f"(git fetch origin): {exc}"
            ) from exc
    return [line for line in out.split("\n") if line.strip()]


def uncommitted_changes() -> bool:
    """True when the working tree is dirty.

    Fails closed. Assuming "clean" because ``git status`` errored would let a PR
    open that silently omits the work in progress, which is the worst outcome
    this script could produce.
    """
    try:
        return bool(git(["status", "--porcelain"]).strip())
    except ToolError as exc:
        raise PreflightError(
            f"cannot determine working-tree state, refusing to open a PR: {exc}"
        ) from exc


def build_body(closes: int | None, body_file: str | None) -> str:
    if body_file:
        try:
            with open(body_file, encoding="utf-8") as fh:
                supplied = fh.read().strip()
        except OSError as exc:
            raise ToolError(f"cannot read {body_file}: {exc}") from exc
        if not supplied:
            raise PreflightError(f"{body_file} is empty")
        if closes and "Closes #" not in supplied:
            supplied += f"\n\nCloses #{closes}"
        return supplied

    lines = [
        "## What",
        "",
        "_Describe the change and why it is needed. Link the issue it closes._",
        "",
        "## Testing",
        "",
        "_What you ran, and what the result was. This is what lets a maintainer "
        "merge without re-running everything._",
        "",
    ]
    if closes:
        lines += [f"Closes #{closes}"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    _use_utf8_output()
    parser = argparse.ArgumentParser(
        description="Open a well-formed pull request for a change you already made."
    )
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--title", required=True, help="pull request title")
    parser.add_argument("--base", default="main", help="base branch (default: main)")
    parser.add_argument("--closes", type=int, default=None, help="issue number to close")
    parser.add_argument("--body-file", default=None, help="file containing the PR body")
    parser.add_argument(
        "--allow-empty", action="store_true",
        help="open even if the branch has no new commits (not recommended)",
    )
    parser.add_argument("--draft", action="store_true", help="open as a draft")
    parser.add_argument("--dry-run", action="store_true", help="show the plan, open nothing")
    args = parser.parse_args(argv)

    try:
        validate_repo(args.repo)
    except ToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not args.title.strip():
        print("error: --title must not be empty", file=sys.stderr)
        return 1

    try:
        branch = current_branch()
        ahead = commits_ahead(args.base)
        dirty = uncommitted_changes()
        body = build_body(args.closes, args.body_file)
    except PreflightError as exc:
        print(f"pre-flight failed: {exc}", file=sys.stderr)
        return 2
    except ToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if dirty:
        print(
            "pre-flight failed: uncommitted changes. Commit or stash first, "
            "otherwise the PR will not contain your work.",
            file=sys.stderr,
        )
        return 2
    if not ahead and not args.allow_empty:
        print(
            f"pre-flight failed: no commits on {branch!r} beyond origin/{args.base}. "
            "There is nothing to propose. Make the change first.",
            file=sys.stderr,
        )
        return 2

    cmd = [
        "gh", "pr", "create",
        "--repo", args.repo,
        "--base", args.base,
        "--head", branch,
        "--title", args.title,
        "--body", body,
    ]
    if args.draft:
        cmd.append("--draft")

    print(f"branch : {branch}")
    print(f"base   : {args.base}")
    print(f"commits: {len(ahead)}")
    for line in ahead[:10]:
        print(f"  - {line}")
    if len(ahead) > 10:
        print(f"  ... and {len(ahead) - 10} more")

    if args.dry_run:
        print()
        print("dry run; nothing opened. command would be:")
        print(f"  gh pr create --repo {args.repo} --base {args.base} "
              f"--head {branch} --title {args.title!r}")
        return 0

    try:
        url = gh(cmd[1:]).strip()
    except ToolError as exc:
        print(f"error: could not open pull request: {exc}", file=sys.stderr)
        return 1

    print()
    print(f"opened: {url}")
    print()
    print("Before you consider it done:")
    print("  1. Re-read the diff as the maintainer will see it.")
    print("  2. Confirm CI passed.")
    print("  3. Respond to review even if you disagree; an unanswered PR is a closed PR.")
    print("  4. Merge only when you have a review, or the project does not require one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
