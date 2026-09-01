#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""file_vuln_issues.py — File or sync GitHub Issues for achievement-hacking vulnerabilities.

Usage:
    python file_vuln_issues.py                    # file all issues (creates new)
    python file_vuln_issues.py --dry-run          # print what would be filed/updated
    python file_vuln_issues.py --stop-on-error    # exit on first filing failure
    python file_vuln_issues.py --sync             # idempotent sync (update or create)
    python file_vuln_issues.py --sync --dry-run   # show what sync would do

Requires: gh CLI authenticated with repo scope.
"""
import argparse
import subprocess
import sys
import time

REPO = "neohiro/achievement-hacks"

ISSUES = [
    {
        "title": "[VULN-001] Quickdraw: sub-5-minute issue close loop is trivially automatable",
        "labels": ["security", "vulnerability", "vuln-quickdraw", "achievement"],
        "body": """## Summary

The **Quickdraw** achievement (`quickdraw`) is awarded when an issue or PR is closed within 5 minutes of opening. The window is enforceable server-side, but the threshold and lack of human-interaction gate make it **trivially automatable** via a 2-line script.

## Severity

Medium (platform integrity concern, not a data breach)

## PoC

```python
issue = api.create_issue(repo, title="quickdraw test", body="")
api.close_issue(repo, issue.number)  # < 1 second later
# Both opener and closer earn the badge
```

Reference implementation: [neohiro/achievement-hacks/_achievements/quickdraw/earn.sh](https://github.com/neohiro/achievement-hacks/blob/main/_achievements/quickdraw/earn.sh)

Full security analysis: see [SECURITY.md#vuln-001-quickdraw-sub-5-minute-issuepr-close-loop](https://github.com/neohiro/achievement-hacks/blob/main/SECURITY.md#vuln-001-quickdraw-sub-5-minute-issuepr-close-loop)

## Impact

- The Quickdraw badge no longer indicates "fast responder" — it indicates "ran a script."
- The 5-minute window is wide enough that even naive bots can earn the badge.
- No CAPTCHA, no account-age gate, no human-interaction check.

## Proposed Defenses

1. **Time-gap floor:** Require a minimum 60s between open and close to credit the badge. Below 60s = no badge.
2. **Account-age gate:** Require the account to be >= 7 days old before awarding Quickdraw.
3. **Velocity rate limit:** > 3 Quickdraw candidates per 24h on the same account = pause awarding for 7 days.
4. **Behavioral signal:** Require the account to have opened >= 2 non-Quickdraw issues before awarding.
5. **Publish threshold tables:** Disclose the exact conditions for badge award so honest users know what to aim for.

## Reference

- [Achievement docs](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-github-profile/customizing-your-profile/personalizing-your-profile#displaying-badges-on-your-profile)
- [neohiro/achievement-hacks README](https://github.com/neohiro/achievement-hacks)

## Disclosure

Filed responsibly by the [neohiro](https://github.com/neohiro) org. The PoC has been verified; we are filing this as a defensive disclosure to invite mitigation.
""",
    },
    {
        "title": "[VULN-002] YOLO: review-free merge via admin override is one-click automatable",
        "labels": ["security", "vulnerability", "vuln-yolo", "achievement"],
        "body": """## Summary

The **YOLO** achievement (`yolo`) is awarded when a PR is merged without any reviews. Repos with branch protection that requires reviews should block this, but **admin override** allows admins to bypass the review requirement. A single-click script can farm the badge.

## Severity

Low (requires admin access, which is already a position of trust)

## PoC

```bash
pr_url=$(gh pr create --repo myorg/myrepo --title yolo --body yolo)
gh pr merge --admin --squash "$pr_url"
# Badge earned
```

Reference: [neohiro/achievement-hacks/_achievements/yolo/README.md](https://github.com/neohiro/achievement-hacks/blob/main/_achievements/yolo/README.md)

## Impact

- YOLO is self-deprecating by design. The badge humorously rewards "no review" behavior.
- The admin-override path is the only real automation vector. Without admin rights, the badge requires legitimate lack of branch protection.

## Proposed Defenses

1. **Exclude admin-override merges:** Only count merges where the reviewer requirement was genuinely absent (repo never required reviews). Admin overrides should not count.
2. **Rate-limit YOLO awards:** Cap YOLO awards to 1 per account per 90 days. Prevents farming across multiple repos.
3. **Repo-age gate:** YOLO only earns on repos >= 30 days old. Prevents throwaway repo farms.

## Reference

- [Full security analysis](https://github.com/neohiro/achievement-hacks/blob/main/SECURITY.md#vuln-002-yolo-review-free-merge-via-admin-override)
- [neohiro/achievement-hacks README](https://github.com/neohiro/achievement-hacks)

## Disclosure

Filed responsibly by the [neohiro](https://github.com/neohiro) org.
""",
    },
    {
        "title": "[VULN-003] Heart On Your Sleeve: mass reaction automation is undetectable at scale",
        "labels": ["security", "vulnerability", "vuln-heart-on-your-sleeve", "achievement"],
        "body": """## Summary

The **Heart On Your Sleeve** achievement (`heart-on-your-sleeve`) is awarded when a user adds a heart reaction (❤️) to any comment or discussion. The tier thresholds are not publicly disclosed. Mass-reaction automation is trivially scriptable and appears to operate without rate-limit detection at small-to-moderate scale.

## Severity

Low (likely ToS violation, but not yet formally detected)

## PoC

```python
for comment_url in scraped_comment_urls:
    api.add_reaction(comment_url, "heart")
    time.sleep(random.uniform(1, 3))  # naive anti-detection
```

**Note:** Automated mass reactions likely violate GitHub ToS. This is documented for research purposes only.

Reference: [neohiro/achievement-hacks/_achievements/heart-on-your-sleeve/README.md](https://github.com/neohiro/achievement-hacks/blob/main/_achievements/heart-on-your-sleeve/README.md)

## Impact

- Heart On Your Sleeve no longer indicates genuine engagement appreciation.
- Mass reactions could be used to harass users (notification spam).
- Tier thresholds being unpublished makes honest users blind to what they are working toward.

## Proposed Defenses

1. **Rate limit reactions:** Max 10 heart reactions per hour per account. Graduated per-account-age limits.
2. **Reaction diversity check:** Require >= 3 different reaction types (not just heart) before heart reactions start counting.
3. **Human interaction gate:** Require the account to have >= 5 manual (non-API) interactions in the past 30 days before reactions count.
4. **ToS enforcement:** Actively detect and suspend accounts using automated reaction scripts.
5. **Publish tier thresholds:** Disclose Bronze/Silver/Gold criteria so honest users know what to work toward.

## Reference

- [Full security analysis](https://github.com/neohiro/achievement-hacks/blob/main/SECURITY.md#vuln-003-heart-on-your-sleeve-mass-reaction-automation)

## Disclosure

Filed responsibly by the [neohiro](https://github.com/neohiro) org.
""",
    },
    {
        "title": "[VULN-004] Pair Extraordinaire: single PR can farm entire co-author counter",
        "labels": ["security", "vulnerability", "vuln-pair-extraordinaire", "achievement"],
        "body": """## Summary

The **Pair Extraordinaire** achievement (`pair-extraordinaire`) counts co-authored commits on merged PRs. A single PR with 50 commits, each carrying a `Co-authored-by:` trailer, increments the counter by 50 in one go. There is no cap on co-authored commits per PR.

## Severity

Low (requires one real GitHub co-author account)

## PoC

```bash
for i in {1..50}; do
  git commit --allow-empty -m "chore: attestation $i

Co-authored-by: Bot Account <bot@users.noreply.github.com>"
done
gh pr create --title "attestation run" --body ""
gh pr merge --squash
# Both accounts get +50 toward Pair Extraordinaire
```

Reference: [neohiro/achievement-hacks/_achievements/pair-extraordinaire/README.md](https://github.com/neohiro/achievement-hacks/blob/main/_achievements/pair-extraordinaire/README.md)

## Impact

- A single PR can farm Bronze (10) → Silver (24) → Gold (48) in one merge.
- `Co-authored-by:` validates account existence, so two real accounts are required. But bot networks with paired accounts defeat this.

## Proposed Defenses

1. **Merge-size normalization:** Only count unique commits with co-authors, not total commits. One PR with 50 co-authored commits should count as 1, not 50.
2. **Co-author diversity check:** Require >= N unique co-author accounts (not just one account farming itself).
3. **Commit quality gate:** Require the commit to have a minimum diff size (>= 3 lines changed) before the co-author counts.
4. **PR merge frequency cap:** If > 5 co-authored PRs from the same pair of accounts in 7 days, pause badge awarding for 30 days.

## Reference

- [Full security analysis](https://github.com/neohiro/achievement-hacks/blob/main/SECURITY.md#vuln-004-pair-extraordinaire-co-author-trailer-abuse)
- [GitHub co-author documentation](https://docs.github.com/en/pull-requests/committing-changes-to-your-project/creating-and-editing-commits/creating-a-commit-with-multiple-authors)

## Disclosure

Filed responsibly by the [neohiro](https://github.com/neohiro) org.
""",
    },
    {
        "title": "[VULN-005] Pull Shark: count-based metric is farming-friendly",
        "labels": ["security", "vulnerability", "vuln-pull-shark", "achievement"],
        "body": """## Summary

The **Pull Shark** achievement (`pull-shark`) counts merged PRs. There is no diversity, diff-size, or velocity weighting. A script can open 16 trivial PRs and self-merge them as admin, earning Bronze in under an hour.

## Severity

Low (PRs require merge action, which provides some friction)

## PoC

```python
for i in range(20):
    pr = api.create_pr(repo, title=f"chore: {i}", body="")
    api.set_labels(pr, ["trivial"])
    api.merge_pr(pr.number, admin_bypass=True)
    time.sleep(60)
```

Reference: [neohiro/achievement-hacks/_achievements/pull-shark/README.md](https://github.com/neohiro/achievement-hacks/blob/main/_achievements/pull-shark/README.md)

## Impact

- Pull Shark Gold (1024 PRs) could theoretically be farmed by a bot in weeks.
- Low harm: PR farming is the closest thing to "real work" among the automation vectors.
- Natural defense: Meaningful PRs take time to review and merge. The real bottleneck is review time, not script speed.

## Proposed Defenses

1. **Breadth weighting:** Reward PRs across many different repositories more than PRs on the same repo. 10 PRs across 10 repos > 100 PRs on 1 repo.
2. **Merge velocity cap:** If > 5 PRs are merged within 1 hour on the same account, pause badge awarding for 24 hours.
3. **Diff size normalization:** Award 1 point per merged PR for PRs with < 10 lines changed; 2 points for 10-100 lines; 5 points for 100+ lines.
4. **Time decay:** PRs older than 2 years count at 50% for badge tiers.

## Reference

- [Full security analysis](https://github.com/neohiro/achievement-hacks/blob/main/SECURITY.md#vuln-005-pull-shark-automated-pr-farming)

## Disclosure

Filed responsibly by the [neohiro](https://github.com/neohiro) org.
""",
    },
    {
        "title": "[VULN-006] Galaxy Brain: self-answered Q&A discussions can farm the badge",
        "labels": ["security", "vulnerability", "vuln-galaxy-brain", "achievement"],
        "body": """## Summary

The **Galaxy Brain** achievement (`galaxy-brain`) counts accepted answers in GitHub Discussions (Q&A category). A user who is both the question asker and the answerer (legitimate for FAQs) can self-accept and earn the badge repeatedly.

## Severity

Low (the self-answer pattern is also the recommended way to create FAQs)

## PoC

```python
for i in range(10):
    d = api.create_discussion(category="Q&A", title=f"FAQ: How do I configure {i}?", body="See replies.")
    a = api.create_discussion_comment(d, "Here is the answer.")
    api.accept_discussion_answer(d, a)
    # +1 Galaxy Brain per accepted answer
```

Reference: [neohiro/achievement-hacks/_achievements/galaxy-brain/README.md](https://github.com/neohiro/achievement-hacks/blob/main/_achievements/galaxy-brain/README.md)

## Impact

- Self-answered FAQs are genuinely useful — the issue is the abuse of the mechanism for badge farming.
- Throws the achievement's value as a "helpful expert" signal into question.

## Proposed Defenses

1. **Self-answer weighting:** If the answerer is the same account as the question asker, the answer counts at 25% weight. Requires 4 self-answers for 1 effective credit.
2. **Q&A category gate:** Only Q&A discussions in repos with >= 50 stars count. Prevents throwaway repo farms.
3. **Minimum repo age:** Galaxy Brain only earns on repos >= 90 days old.
4. **Accept rate normalization:** Only count answers accepted by a **different** account. Or: require at least one upvote from a different account before accepting.

## Reference

- [Full security analysis](https://github.com/neohiro/achievement-hacks/blob/main/SECURITY.md#vuln-006-galaxy-brain-discussion-self-answer-abuse)

## Disclosure

Filed responsibly by the [neohiro](https://github.com/neohiro) org.
""",
    },
]


def build_command(issue):
    """Build the gh issue create command for a single issue.

    Exposed for testing; do not invoke subprocess here.
    """
    cmd = [
        "gh", "issue", "create",
        "--repo", REPO,
        "--title", issue["title"],
        "--body", issue["body"],
    ]
    for label in issue["labels"]:
        cmd += ["--label", label]
    return cmd


def _gh_run(cmd):
    """Default runner: wraps subprocess.run with the correct flags for gh.

    Uses errors="replace" so a stray non-UTF8 byte in gh stderr never crashes
    the whole run. gh rarely emits non-UTF8, but it can happen on Windows
    when locale is not UTF-8.
    """
    return subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")


# Rate-limit handling: gh returns HTTP 429 as a non-zero exit code with a
# Retry-After hint in stderr. We retry with exponential backoff up to 3 times.
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2  # seconds — 2, 4, 8


def _is_rate_limited(stderr: str) -> bool:
    """Heuristic: gh surfaces rate limits as a non-zero exit with a 429-ish message."""
    return "429" in stderr or "rate limit" in stderr.lower()


def _retry_gh_run(cmd, max_retries=_MAX_RETRIES):
    """Run gh with exponential-backoff retry on rate-limit (429) responses.

    Returns the CompletedProcess from the final attempt. Raises the last
    exception if every attempt fails.
    """
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            result = _gh_run(cmd)
        except FileNotFoundError:
            raise  # gh not installed — no point retrying
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(_RETRY_BACKOFF_BASE ** attempt)
                continue
            raise
        if result.returncode == 0:
            return result
        if _is_rate_limited(result.stderr) and attempt < max_retries:
            time.sleep(_RETRY_BACKOFF_BASE ** attempt)
            continue
        return result  # non-rate-limit failure — return as-is
    if last_exc:
        raise last_exc
    return result  # pragma: no cover — defensive fallback


def file_issues(dry_run=False, stop_on_error=False, runner=None):
    """File all issues. Returns 0 on full success, 1 on first failure (when stop_on_error).

    runner: optional callable(cmd) -> CompletedProcess. Defaults to _gh_run.
          A runner that yields non-zero returncodes on rate-limit will be retried
          internally by _retry_gh_run when the default runner is used. When an
          injected mock runner is used (for testing), no retry is applied.
    """
    if runner is None:
        runner = _retry_gh_run

    success_count = 0
    failure_count = 0

    for i, issue in enumerate(ISSUES, 1):
        cmd = build_command(issue)
        print(f"[{i}/{len(ISSUES)}] {'[DRY-RUN]' if dry_run else 'Running'} gh issue create --repo {REPO} --title {issue['title']!r}", file=sys.stderr)

        if dry_run:
            continue

        try:
            result = runner(cmd)
        except FileNotFoundError:
            print(f"ERR: 'gh' CLI not found — install it from https://cli.github.com", file=sys.stderr)
            failure_count += 1
            if stop_on_error:
                return 1
            continue
        except Exception as exc:
            print(f"ERR: runner raised {type(exc).__name__}: {exc}", file=sys.stderr)
            failure_count += 1
            if stop_on_error:
                return 1
            continue

        if result.returncode == 0:
            print(f"OK: {result.stdout.strip()}", file=sys.stderr)
            success_count += 1
        else:
            # Scrub potential token leaks from stderr before logging
            safe_err = _scrub_sensitive(result.stderr.strip())
            print(f"ERR: {safe_err}", file=sys.stderr)
            failure_count += 1
            if stop_on_error:
                print(f"Stopping on error at issue {i}.", file=sys.stderr)
                return 1

    print(f"Summary: {success_count} succeeded, {failure_count} failed out of {len(ISSUES)}", file=sys.stderr)
    return 1 if failure_count else 0


def _scrub_sensitive(text: str) -> str:
    """Remove likely GitHub token values from error strings before logging."""
    import re
    text = re.sub(r"gh[pousr]_[A-Za-z0-9_]+", "ghp_***REDACTED***", text)
    text = re.sub(r"github_pat_[A-Za-z0-9_]+", "github_pat_***REDACTED***", text)
    return text


def _extract_vuln_id(title: str) -> str | None:
    """Return the VULN-### prefix from an issue title, or None."""
    import re
    m = re.search(r"\[(VULN-\d{3})\]", title)
    return m.group(1) if m else None


def _fetch_existing_issues(runner=None) -> dict[str, dict]:
    """Fetch all open/closed issues labeled 'vulnerability' for this repo.

    Returns a dict keyed by VULN-### id -> {number, title, body, state}.
    Uses _retry_gh_run so rate-limits are retried.
    """
    if runner is None:
        runner = _retry_gh_run

    result = runner(["gh", "issue", "list",
                     "--repo", REPO,
                     "--json", "number,title,body,state",
                     "--label", "vulnerability",
                     "--state", "all",
                     "--limit", "100"])
    if result.returncode != 0:
        raise RuntimeError(f"gh issue list failed: {result.stderr.strip()}")
    import json
    raw = result.stdout.strip()
    if not raw:
        return {}
    try:
        issues = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh issue list returned invalid JSON: {exc}\n{raw[:200]}")

    out = {}
    for issue in issues:
        vid = _extract_vuln_id(issue.get("title", ""))
        if vid:
            out[vid] = issue
    return out


def _body_matches(local_body: str, remote_body: str) -> bool:
    """Return True if local_body and remote_body are equivalent for sync purposes.

    Compares after stripping trailing whitespace. Whitespace differences in
    multi-line bodies are ignored. This handles CRLF/LF differences between
    platforms and formatting variation in how the body was written.
    """
    import difflib
    local_lines = [ln.rstrip() for ln in local_body.splitlines()]
    remote_lines = [ln.rstrip() for ln in remote_body.splitlines()]
    diff = list(difflib.unified_diff(remote_lines, local_lines, lineterm=""))
    return len(diff) == 0


def sync_issues(dry_run=False, runner=None):
    """Fetch existing VULN-### issues and update any whose body differs from ISSUES.

    Idempotent: safe to run repeatedly. Issues are matched by their [VULN-###]
    title prefix. Only issues labeled 'vulnerability' are considered.

    Returns exit code: 0 = all up to date (or all dry-run changes applied),
                      1 = at least one real update failed.
    """
    if runner is None:
        runner = _retry_gh_run

    print(f"[SYNC] Fetching existing issues from {REPO} ...", file=sys.stderr)
    try:
        existing = _fetch_existing_issues(runner=runner)
    except RuntimeError as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 1

    print(f"[SYNC] Found {len(existing)} existing vulnerability issues.", file=sys.stderr)

    create_needed = {i: issue for i, issue in enumerate(ISSUES)
                     if _extract_vuln_id(issue["title"]) not in existing}
    update_needed = []
    up_to_date = []

    for issue in ISSUES:
        vid = _extract_vuln_id(issue["title"])
        if vid and vid in existing:
            remote = existing[vid]
            if _body_matches(issue["body"], remote.get("body", "")):
                up_to_date.append(vid)
            else:
                update_needed.append((vid, remote["number"], issue))

    created = updated = failed = 0

    for vid in up_to_date:
        print(f"[SYNC] OK     {vid}: up to date", file=sys.stderr)

    for issue in create_needed.values():
        vid = _extract_vuln_id(issue["title"]) or "?"
        print(f"[SYNC] CREATE {vid}: {issue['title'][:60]} ...", file=sys.stderr)
        if not dry_run:
            cmd = build_command(issue)
            try:
                result = runner(cmd)
            except Exception as exc:
                print(f"[SYNC] ERR    {vid}: runner raised {type(exc).__name__}: {exc}", file=sys.stderr)
                failed += 1
                continue
            if result.returncode == 0:
                print(f"[SYNC] CREATED: {result.stdout.strip()}", file=sys.stderr)
                created += 1
            else:
                print(f"[SYNC] ERR    {vid}: {_scrub_sensitive(result.stderr.strip())}", file=sys.stderr)
                failed += 1

    for vid, number, issue in update_needed:
        print(f"[SYNC] UPDATE {vid} (#{number}): {issue['title'][:60]} ...", file=sys.stderr)
        if not dry_run:
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            ) as f:
                f.write(issue["body"])
                tmp = f.name
            result = runner(["gh", "issue", "edit", str(number),
                             "--repo", REPO, "--body-file", tmp])
            import os
            os.unlink(tmp)
            if result.returncode == 0:
                print(f"[SYNC] UPDATED: #{number}", file=sys.stderr)
                updated += 1
            else:
                print(f"[SYNC] ERR    {vid}: {_scrub_sensitive(result.stderr.strip())}", file=sys.stderr)
                failed += 1

    print(f"[SYNC] Done. Up-to-date={len(up_to_date)}  Created={created}  "
          f"Updated={updated}  Failed={failed}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="File or sync GitHub Issues for achievement-hacking vulnerabilities."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be filed/updated without doing it")
    parser.add_argument("--stop-on-error", action="store_true",
                        help="Exit on first filing failure instead of continuing")
    parser.add_argument("--sync", action="store_true",
                        help="Sync: fetch existing issues, update any that differ from local ISSUES. "
                             "Safe to run repeatedly — idempotent.")
    args = parser.parse_args()
    if args.sync:
        sys.exit(sync_issues(dry_run=args.dry_run))
    sys.exit(file_issues(dry_run=args.dry_run, stop_on_error=args.stop_on_error))
