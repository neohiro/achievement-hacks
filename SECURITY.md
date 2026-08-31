# Security Policy — Achievement Automation Vulnerabilities

> **This document is a security research disclosure by the [neohiro](https://github.com/neohiro) org.**
> It documents low-effort automation vectors for GitHub Achievements and proposes concrete defenses.
> Filed as GitHub Issues: see [#1](./issues?q=label%3Avuln-achievement), [#2](./issues?q=label%3Avuln-quickdraw), etc.
>
> **Responsible disclosure:** These are platform-level concerns. We are documenting them here
> to (a) inform GitHub's security team and (b) invite the community to discuss mitigation strategies.
> Do not use the automation patterns described here to farm achievements on accounts you don't own.

---

## Table of Contents

1. [Vulnerability Index](#vulnerability-index)
2. [Background](#background)
3. [VULN-001: Quickdraw — Sub-5-Minute Issue/PR Close Loop](#vuln-001-quickdraw--sub-5-minute-issuepr-close-loop)
4. [VULN-002: YOLO — Review-Free Merge via Admin Override](#vuln-002-yolo--review-free-merge-via-admin-override)
5. [VULN-003: Heart On Your Sleeve — Mass Reaction Automation](#vuln-003-heart-on-your-sleeve--mass-reaction-automation)
6. [VULn-004: Pair Extraordinaire — Co-Author Trailer Abuse](#vuln-004-pair-extraordinaire--co-author-trailer-abuse)
7. [VULN-005: Pull Shark — Automated PR Farming](#vuln-005-pull-shark--automated-pr-farming)
8. [VULN-006: Galaxy Brain — Discussion Self-Answer Abuse](#vuln-006-galaxy-brain--discussion-self-answer-abuse)
9. [Proposed Defenses](#proposed-defenses)
10. [Disclosure Timeline](#disclosure-timeline)

---

## Vulnerability Index

| ID | Achievement | Severity | Automation Difficulty | Exploitability |
|---|---|---|---|---|
| VULN-001 | Quickdraw | **Medium** | Trivial | Anyone with repo access |
| VULN-002 | YOLO | **Low** | Trivial | Admin-only |
| VULN-003 | Heart On Your Sleeve | **Low** | Trivial | Any account with reactions access |
| VULN-004 | Pair Extraordinaire | **Low** | Easy | Requires one real collaborator |
| VULN-005 | Pull Shark | **Low** | Easy | Any account with push access |
| VULN-006 | Galaxy Brain | **Low** | Medium | Requires self-ask + self-answer |

---

## Background

GitHub Achievements were introduced June 2022 as profile badges celebrating meaningful contributions.
Each achievement tracks a specific behavior (merged PRs, stars, reactions, etc.). The thresholds for
the lower tiers of most achievements are low enough that automated scripts can earn them within minutes.

This document focuses on the **achievements that are mechanically trivial to automate** — not because
the community will misuse them maliciously, but because the thresholds are misaligned with the
adversarial landscape of bot-farmed achievement accounts.

The spirit of achievements is to celebrate **real, sustained, human contribution**. Automated farming
undermines that spirit and degrades the value of badges on genuine developer profiles.

---

## VULN-001: Quickdraw — Sub-5-Minute Issue/PR Close Loop

**Achievement:** 🔫 Quickdraw (`quickdraw`)
**Severity:** Medium
**CVSS 3.1 Estimate:** 4.3 (AV:N/AC:L/PR:H/UI:N/S:U/C:N/I:L/A:N)

### Description

The Quickdraw achievement is awarded when an issue or pull request is **closed within 5 minutes**
of being opened. The window is measured from the creation timestamp to the close timestamp.

This is trivially automatable: a script can create an issue and close it within seconds, earning
the badge instantly for both the opener and the closer.

```python
# Pseudocode — VULN-001 PoC (informational only)
issue = api.create_issue(repo, title="quickdraw test", body="")
api.close_issue(repo, issue.number)  # seconds later
# Both opener and closer earn the badge
```

### Impact

- **Badge integrity:** Anyone with push access to a public repo can earn Quickdraw instantly.
- **False signal:** A Quickdraw badge no longer indicates "fast responder" — it indicates "ran a script."
- **Low direct harm:** This is a low-severity platform integrity concern. It does not enable further exploits.

### Evidence

- Automated issue create → close in < 1 second via GitHub REST API is permitted with no rate limit.
- Both the issue opener and the closer earn the badge (doubling exploit value).
- The 5-minute window is enforced server-side but is wide enough to be trivially exploitable.
- No CAPCHA, no account-age gate, no human-interaction check.

### Proposed Defenses

| Defense | Description | Difficulty |
|---|---|---|
| **D1: Time-gap enforcement** | Require a minimum of 60 seconds between open and close to credit the badge. Below 60s = no badge. | Easy |
| **D2: Account-age gate** | Require the account to be at least 7 days old before awarding Quickdraw. New accounts cannot farm it. | Medium |
| **D3: Rate limit on badge triggers** | If > 3 Quickdraw candidates within 24 hours on the same account, suspend awarding for 7 days. | Easy |
| **D4: Behavioral signal** | Require the account to have opened ≥ 2 other issues (non-quickdraw) before awarding. Real users open multiple issues; bots don't. | Medium |
| **D5: Publish threshold tables** | Publicly disclose the exact conditions for badge award so honest users know what to aim for. | Trivial |

### References

- [Quickdraw achievement docs](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-github-profile/customizing-your-profile/personalizing-your-profile#displaying-badges-on-your-profile)
- [GitHub REST API: Create an issue](https://docs.github.com/en/rest/issues/issues#create-an-issue)
- [GitHub REST API: Update an issue](https://docs.github.com/en/rest/issues/issues#update-an-issue)
- Related issue: [#1](./issues/1)

---

## VULN-002: YOLO — Review-Free Merge via Admin Override

**Achievement:** 🏴 YOLO (`yolo`)
**Severity:** Low
**CVSS 3.1 Estimate:** 2.8 (AV:N/AC:H/PR:H/UI:N/S:U/C:N/I:L/A:N)

### Description

The YOLO achievement is awarded when a pull request is **merged without any reviews**.
On repos with branch protection that requires reviews, this is blocked. However, repository
admins can bypass branch protection rules and merge without reviews by using the admin override.

A script can:
1. Open a PR
2. Merge it as admin (bypassing the review requirement)
3. Earn YOLO instantly

```bash
# Pseudocode — VULN-002 PoC
pr = api.create_pr(repo, title="initial commit", body="yolo")
api.merge_pr(repo, pr.number, admin_bypass=True)
# Badge earned
```

### Impact

- **Badge integrity:** Admins on any public repo they own can earn YOLO in one click.
- **Low direct harm:** This requires admin access, which is already a position of trust.
- **Side note:** YOLO is self-deprecating — the badge is humorous by design. This is more of a
  design observation than a security vulnerability.

### Proposed Defenses

| Defense | Description | Difficulty |
|---|---|---|
| **D1: Exclude admin-override merges** | Only count merges where the reviewer requirement was genuinely absent (repo never required reviews). Admin overrides should not count. | Medium |
| **D2: Rate limit YOLO awards** | Cap YOLO awards to 1 per account per 90 days. Prevents farming across multiple repos. | Easy |
| **D3: Repo-age gate** | YOLO only earns on repos ≥ 30 days old. Prevents throwaway repo farms. | Easy |

### References

- Related issue: [#2](./issues/2)

---

## VULN-003: Heart On Your Sleeve — Mass Reaction Automation

**Achievement:** ❤️ Heart On Your Sleeve (`heart-on-your-sleeve`)
**Severity:** Low
**CVSS 3.1 Estimate:** 3.1 (AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:L/A:N)

### Description

The Heart On Your Sleeve achievement is awarded when a user adds a heart reaction (❤️) to any
comment or discussion. The thresholds for tier progression are not publicly disclosed.

A script can automate heart reactions across thousands of comments in a loop:

```python
# Pseudocode — VULN-003 PoC (against GitHub ToS — informational only)
for comment_url in scraped_comment_urls:
    api.add_reaction(comment_url, "heart")
    time.sleep(random.uniform(1, 3))  # slight delay to evade naive rate detection
```

**Note:** Automated mass reactions are likely a violation of GitHub's Terms of Service.
This is documented here for completeness and defense research only.

### Impact

- **Badge integrity:** Heart On Your Sleeve no longer indicates genuine engagement appreciation.
- **Spam risk:** Mass reactions could be used to harass users (bombard them with notifications).
- **ToS concern:** Automated reactions may expose the farming account to suspension.

### Proposed Defenses

| Defense | Description | Difficulty |
|---|---|---|
| **D1: Rate limit reactions per account** | Max 10 heart reactions per hour per account. Graduated per-account limits based on account age. | Easy |
| **D2: Reaction diversity check** | Require at least 3 different reaction types (not just heart) before heart reactions start counting toward the badge. | Medium |
| **D3: Human interaction gate** | Require the account to have had ≥ 5 manual (non-API) interactions in the past 30 days before reactions count. | Medium |
| **D4: ToS enforcement** | Actively detect and suspend accounts using automated reaction scripts. | Hard |

### References

- Related issue: [#3](./issues/3)

---

## VULN-004: Pair Extraordinaire — Co-Author Trailer Abuse

**Achievement:** 👥 Pair Extraordinaire (`pair-extraordinaire`)
**Severity:** Low
**CVSS 3.1 Estimate:** 3.8 (AV:N/AC:L/PR:H/UI:N/S:U/C:N/I:L/A:N)

### Description

The Pair Extraordinaire achievement is awarded for co-authoring commits on merged pull requests.
The `Co-authored-by:` trailer in git commit messages is the mechanism. A script can:

1. Create a PR with many empty/filler commits, each with a `Co-authored-by:` trailer
2. Merge the PR
3. All co-authors on all commits earn the badge

```bash
# Pseudocode — VULN-004 PoC
for i in {1..50}; do
  git commit --allow-empty -m "chore: attestation $i

Co-authored-by: Bot Account <bot@users.noreply.github.com>"
done
gh pr create --title "attestation run" --body ""
gh pr merge --squash
# Both accounts get +50 toward Pair Extraordinaire
```

### Impact

- **Badge integrity:** A single PR can farm the entire Bronze → Silver → Gold chain for a pair of accounts.
- **Syllabus note:** `Co-authored-by:` requires a **real GitHub account**. Fake emails don't work because GitHub validates the account existence.

### Proposed Defenses

| Defense | Description | Difficulty |
|---|---|---|
| **D1: Merge-size normalization** | Only count unique commits with co-authors, not total commits. One PR with 50 co-authored commits should count as 1, not 50. | Medium |
| **D2: Co-author diversity check** | Require at least N unique co-author accounts (not just one account farming itself). | Medium |
| **D3: Commit quality gate** | Require the commit to have a minimum diff size (e.g., ≥ 3 lines changed) before the co-author counts. | Easy |
| **D4: PR merge frequency cap** | If > 5 co-authored PRs from the same pair of accounts in 7 days, pause badge awarding for 30 days. | Easy |

### References

- [GitHub co-author documentation](https://docs.github.com/en/pull-requests/committing-changes-to-your-project/creating-and-editing-commits/creating-a-commit-with-multiple-authors)
- Related issue: [#4](./issues/4)

---

## VULN-005: Pull Shark — Automated PR Farming

**Achievement:** 🦈 Pull Shark (`pull-shark`)
**Severity:** Low
**CVSS 3.1 Estimate:** 3.5 (AV:N/AC:L/PR:H/UI:N/S:U/C:N/I:L/A:N)

### Description

The Pull Shark achievement counts merged PRs. A script can open a large number of small PRs
and merge them (or have them merged) to climb the tiers. At Bronze (16 PRs), this is trivial
for any active account. At Gold (1024 PRs), it requires sustained automation.

```python
# Pseudocode — VULN-005 PoC
for i in range(20):
    pr = api.create_pr(repo=f"neohiro/repo", title=f"chore: {i}", body="")
    api.set_labels(pr, ["trivial"])
    api.merge_pr(pr.number)
    time.sleep(60)  # avoid rapid-fire detection
```

### Impact

- **Badge integrity:** Pull Shark Gold (1024 PRs) could theoretically be farmed by a bot in weeks.
- **Low harm:** PR farming is the closest thing to "real work" among the automation vectors.
- **Natural defense:** Meaningful PRs take time to review and merge. The real bottleneck is review time, not script speed.

### Proposed Defenses

| Defense | Description | Difficulty |
|---|---|---|
| **D1: Breadth weighting** | Reward PRs across many different repositories more than PRs on the same repo. 10 PRs across 10 repos > 100 PRs on 1 repo. | Medium |
| **D2: Merge velocity cap** | If > 5 PRs are merged within 1 hour on the same account, pause badge awarding for 24 hours. | Easy |
| **D3: Diff size normalization** | Award 1 point per merged PR for PRs with < 10 lines changed; 2 points for 10–100 lines; 5 points for 100+ lines. | Medium |
| **D4: Time decay** | PRs older than 2 years count at 50% for badge tiers. Current contribution is valued more. | Medium |

### References

- Related issue: [#5](./issues/5)

---

## VULN-006: Galaxy Brain — Discussion Self-Answer Abuse

**Achievement:** 🧠 Galaxy Brain (`galaxy-brain`)
**Severity:** Low
**CVSS 3.1 Estimate:** 2.5 (AV:N/AC:H/PR:H/UI:R/S:U/C:N/I:L/A:N)

### Description

The Galaxy Brain achievement is awarded for having answers accepted in GitHub Discussions (Q&A category).
A self-answer pattern can farm this:

1. Create a Q&A discussion with a question
2. Answer it yourself
3. Mark your own answer accepted (if you are the repo admin or the question asker)
4. Repeat N times

```python
# Pseudocode — VULN-006 PoC
for i in range(10):
    discussion = api.create_discussion(
        category="Q&A",
        title=f"FAQ: How do I configure {i}?",
        body="Answer in the replies."
    )
    answer = api.create_discussion_comment(discussion, "Here's how...")
    api.accept_discussion_answer(discussion, answer)
    # +1 Galaxy Brain per accepted answer
```

### Impact

- **Badge integrity:** Self-answered FAQs can farm the entire achievement chain.
- **Legitimate use case:** Self-answered FAQs are genuinely useful. The issue is the abuse of the mechanism.
- **Low harm:** The self-answer pattern is actually the recommended way to create FAQs on GitHub Discussions.

### Proposed Defenses

| Defense | Description | Difficulty |
|---|---|---|
| **D1: Self-answer weighting** | If the answerer is the same account as the question asker, the answer counts at 25% weight. Requires 4 self-answers for 1 effective credit. | Medium |
| **D2: Q&A category gate** | Only Q&A discussions in repos with ≥ 50 stars count. Prevents throwaway repo farms. | Easy |
| **D3: Minimum repo age** | Galaxy Brain only earns on repos ≥ 90 days old. Prevents quick throwaway repo setups. | Easy |
| **D4: Accept rate normalization** | Only count answers accepted by a **different** account. Or: require at least one upvote from a different account before accepting. | Medium |

### References

- Related issue: [#6](./issues/6)

---

## Proposed Defenses

The following cross-cutting defenses would address multiple vulnerabilities simultaneously:

### Global Defenses (High Impact)

| ID | Defense | Addresses | Difficulty |
|---|---|---|---|
| **G1** | **Account-age gate:** Require accounts to be ≥ 30 days old before awarding any activity-based achievement. Prevents throwaway bot account farms. | VULN-001, 002, 003, 004, 005, 006 | Easy |
| **G2** | **Velocity rate limiting:** Cap the rate at which any single behavior can trigger badge increments (e.g., max 5 Quickdraw candidates per 24h per account). | VULN-001, 002, 005 | Easy |
| **G3** | **Breadth scoring:** Weight achievements by diversity of repos/accounts involved, not just raw counts. A PR merged across 10 repos counts more than 10 on the same repo. | VULN-004, 005, 006 | Medium |
| **G4** | **Publish threshold tables:** GitHub should publish the exact tier thresholds for Heart On Your Sleeve and Open Sourcerer so honest users know what to work toward. | All | Trivial |
| **G5** | **Behavioral signal audit:** Before awarding a badge, check the account for minimum genuine activity (issues opened, comments made, stars received). Accounts with only the badge-triggering behavior should not receive the badge. | VULN-001, 003, 004 | Medium |

### Privacy Note

All proposed defenses respect user privacy. None of the above defenses require inspecting private repositories or exposing user behavior data. They operate on public signals: account age, public PR/issue count, public star counts, and public reaction activity.

---

## Disclosure Timeline

| Date | Event |
|---|---|
| 2026-08-31 | Vulnerabilities documented in `neohiro/achievementhacks` repository |
| 2026-08-31 | GitHub Issues filed as public security concerns |
| 2026-08-31 | GitHub Security team notified via [HackerOne GitHub Bug Bounty](https://hackerone.com/github) (if applicable) |
| TBD | GitHub acknowledges / implements defenses |
| TBD | This document updated with resolution status |

---

## License

This security disclosure is published under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The automation scripts described in this document are for **research and defense purposes only**.
Do not use them to farm achievements on accounts you don't own. Such use likely violates GitHub's Terms of Service.
