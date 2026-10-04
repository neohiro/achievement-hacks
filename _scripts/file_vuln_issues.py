#!/usr/bin/env python3
"""file_vuln_issues.py — File GitHub Issues for achievement-hacking vulnerabilities.

Usage:
    python file_vuln_issues.py              # file all issues
    python file_vuln_issues.py --dry-run     # print what would be filed
    python file_vuln_issues.py --stop-on-error  # exit on first failure

Requires: gh CLI authenticated with repo scope.
"""
import argparse
import subprocess
import sys

REPO = "neohiro/achievement-hacks"

# Seconds before a single `gh` invocation is abandoned. An unattended run should
# fail cleanly rather than block on an auth prompt.
GH_TIMEOUT = 120

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

Full security analysis: see [SECURITY.md#vuln-001-quickdraw--sub-5-minute-issuepr-close-loop](https://github.com/neohiro/achievement-hacks/blob/main/SECURITY.md#vuln-001-quickdraw--sub-5-minute-issuepr-close-loop)

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

- [Full security analysis](https://github.com/neohiro/achievement-hacks/blob/main/SECURITY.md#vuln-002-yolo--review-free-merge-via-admin-override)
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

- [Full security analysis](https://github.com/neohiro/achievement-hacks/blob/main/SECURITY.md#vuln-003-heart-on-your-sleeve--mass-reaction-automation)

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

- [Full security analysis](https://github.com/neohiro/achievement-hacks/blob/main/SECURITY.md#vuln-004-pair-extraordinaire--co-author-trailer-abuse)
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

- [Full security analysis](https://github.com/neohiro/achievement-hacks/blob/main/SECURITY.md#vuln-005-pull-shark--automated-pr-farming)

## Disclosure

Filed responsibly by the [neohiro](https://github.com/neohiro) org.
""",
    },
    {
        "title": "[VULN-006] RETRACTED Galaxy Brain: self-answer abuse is not possible "
                 "(acceptance must come from a different account)",
        "labels": ["security", "vulnerability", "vuln-galaxy-brain", "achievement",
                   "retracted"],
        "body": """## RETRACTED — this report was wrong

We filed this on 2026-08-31 claiming that Galaxy Brain could be farmed by asking a
question, answering it yourself, and accepting your own answer as repo admin.

**That is not possible.** GitHub requires the acceptance to be made by a different
account than the answer author. We tested our own recipe and it does not work.

## What we did

Following the recipe above exactly, on 2026-10-03:

| Field | #7 | #19 |
|---|---|---|
| Category | Q&A | Q&A |
| isAnswered | true | true |
| answerChosenAt | 2026-10-03T17:40:08Z | 2026-10-03T17:43:27Z |
| Asker | neohiro | neohiro |
| Accepted-answer author | neohiro | neohiro |

Every documented condition was met, including the Default threshold of two accepted
answers. The badge was not awarded. A scan of all 16 discussion-enabled repositories
in our org found no other accepted Q&A answer.

## Why we were wrong

Our original report proposed mitigation D4 — "only count answers accepted by a
different account" — as a *future* hardening measure. It is in fact the shipped
behaviour, at 0% weight rather than the 25% we proposed. We were asking you to
implement a defence you already have.

GitHub Community staff described the change that closed this:

> "they had to change the rules of the Galaxy Brain achievement so that Q&A in
> community discussions didn't count towards the achievement, because some users
> started spamming discussions by making questions with secondary accounts and
> answering with the main one"

GitHub went further than we suggested and disabled achievements in orgs/community
entirely.

## Community corroboration

- "you CAN NOT mark your own answers to your own questions. They have to be marked
  by another user." — orgs/community #27808
- "Self-marked answers do not count to prevent abuse." — orgs/community #18384
- "self-marked answers don't count." — orgs/community #143321

## What we got right

The tier thresholds (2/8/16/32) are the values generally reported in the community.

## What we still think is a real gap

Not a vulnerability — a documentation gap. GitHub publishes neither the tier table
nor the different-accepter rule in its achievement documentation, so contributors
cannot tell what they are working toward. Unpublished thresholds are tracked as
global defence G4 across all achievements in our SECURITY.md.

## Correction

No action needed from you. Sorry for the noise; the rest of our findings are
unaffected. Full write-up including the experiment:
https://github.com/neohiro/achievement-hacks/blob/main/SECURITY.md
""",
    },
    {
        "title": "[VULN-007] Open Sourcerer: badge rewards activity the spam policy penalises",
        "labels": ["security", "vulnerability", "vuln-open-sourcerer", "achievement"],
        "body": """## Summary

The **Open Sourcerer** achievement (`open-sourcerer`) is awarded for having code merged into a
public repository you do not own. It is the only achievement whose earn condition inherently
requires action against a third party's account.

The notable property is not that the badge is scriptable — opening a pull request is a documented
API operation — but that **the badge's reward condition overlaps with behavior GitHub's spam
policy prohibits**. The same pull request can be merged and worth an achievement tier, or closed as
spam and cost the account its ability to contribute. An account can therefore hold Open Sourcerer
while being banned from opening pull requests. The badge and the Terms of Service disagree about
what the same action means.

## Severity

Low as a security matter. No data exposure, no privilege escalation, no system compromise. This is
a platform-integrity and moderation-consistency issue, and we are not claiming otherwise.

## Automation difficulty

Medium. Unlike the Quickdraw or Pull Shark loops, this one cannot be closed by the attacker alone —
a maintainer must review and merge. That review is the natural rate limit. The realistic abuse
pattern is low-volume, high-targeting trivial PRs against small projects with no branch protection
and an absent maintainer; success is probabilistic, which caps its value.

**Note:** We are not including a mass-PR script here, and we will not accept one. Automating writes
against repositories we do not own is spam, regardless of which badge it is meant to earn. See
our automation ethics note.

## Impact

- Open Sourcerer is the badge most likely to be seen on spam-banned accounts, because surviving a
  spam wave is exactly what the tier thresholds reward.
- Tier thresholds are unpublished, so contributors cannot tell whether a genuine first contribution
  is sufficient.
- Small-project maintainers bear the moderation cost; the farming account bears none.

## Proposed Defenses

1. **Exclude sanctioned activity:** Do not count contributions later marked spam by the receiving
   repository, nor contributions from accounts subsequently suspended for abuse. The enforcement
   signal already exists; the badge layer ignores it.
2. **Publish tier thresholds** for Open Sourcerer.
3. **Time decay:** Weight older contributions less so a badge cannot be built once and displayed
   indefinitely.
4. **Reserve higher tiers for breadth:** Require a sustained multi-repo history for Bronze and
   above, so the badge rewards breadth over volume.

## Reference

- [Full analysis](https://github.com/neohiro/achievement-hacks/blob/main/SECURITY.md#vuln-007-open-sourcerer--third-party-pr-spam-as-an-achievement-path)
- [Automation ethics](https://github.com/neohiro/achievement-hacks/blob/main/_docs/AUTOMATION_ETHICS.md)
- [GitHub Acceptable Use Policies](https://docs.github.com/en/site-policy/acceptable-use-policies)

## Disclosure

Filed responsibly by the [neohiro](https://github.com/neohiro) org. This is submitted as a platform
integrity observation, **not** as a security bounty report: it does not affect the confidentiality,
integrity, or availability of GitHub systems or user data.
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

    ``errors="replace"`` matters on Windows, where gh frequently emits output in
    the console codepage rather than UTF-8; without it a single stray byte
    raises UnicodeDecodeError and is reported as a filing failure that never
    happened. ``timeout`` stops a hung or waiting-for-auth gh from blocking
    forever, which for an unattended run means an indefinite hang rather than a
    clean failure.
    """
    return subprocess.run(
        cmd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=GH_TIMEOUT,
    )


def file_issues(dry_run=False, stop_on_error=False, runner=None):
    """File all issues.

    Returns 0 only if every issue was filed successfully, and 1 if any failed.
    ``stop_on_error`` controls only whether the run *aborts early*; it must never
    change the reported outcome. Returning 0 after a total failure would tell
    CI (and the maintainer) that seven security disclosures were published when
    none were, which is the one result this script must never produce.

    runner: optional callable(cmd) -> CompletedProcess. Defaults to _gh_run.
    """
    if runner is None:
        runner = _gh_run

    failures = 0
    filed = 0

    for i, issue in enumerate(ISSUES, 1):
        cmd = build_command(issue)
        print(f"[{i}/{len(ISSUES)}] {'[DRY-RUN]' if dry_run else 'Running'} gh issue create --repo {REPO} --title {issue['title']!r}", file=sys.stderr)

        if dry_run:
            continue

        try:
            result = runner(cmd)
        except FileNotFoundError:
            print("ERR: 'gh' CLI not found — install it from https://cli.github.com", file=sys.stderr)
            failures += 1
            if stop_on_error:
                return 1
            continue
        except subprocess.TimeoutExpired:
            print(f"ERR: 'gh' timed out after {GH_TIMEOUT}s", file=sys.stderr)
            failures += 1
            if stop_on_error:
                return 1
            continue
        except Exception as exc:
            print(f"ERR: runner raised {type(exc).__name__}: {exc}", file=sys.stderr)
            failures += 1
            if stop_on_error:
                return 1
            continue
        if result.returncode == 0:
            filed += 1
            print(f"OK: {result.stdout.strip()}", file=sys.stderr)
        else:
            failures += 1
            print(f"ERR: {result.stderr.strip()}", file=sys.stderr)
            if stop_on_error:
                print(f"Stopping on error at issue {i}.", file=sys.stderr)
                return 1

    if not dry_run:
        print(
            f"Filed {filed}/{len(ISSUES)} issue(s), {failures} failure(s).",
            file=sys.stderr,
        )
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="File GitHub Issues for achievement-hacking vulnerabilities.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be filed without filing")
    parser.add_argument("--stop-on-error", action="store_true",
                        help="Exit on first filing failure instead of continuing")
    args = parser.parse_args()
    sys.exit(file_issues(dry_run=args.dry_run, stop_on_error=args.stop_on_error))
