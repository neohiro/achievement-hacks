# Security Policy — Achievement Automation Vulnerabilities

> **This document is a security research disclosure by the [neohiro](https://github.com/neohiro) org.**
> It documents low-effort automation vectors for GitHub Achievements and proposes concrete defenses.
> Filed as GitHub Issues: [#1](https://github.com/neohiro/achievement-hacks/issues/1) through
> [#6](https://github.com/neohiro/achievement-hacks/issues/6).
> **VULN-007 is documented but not yet filed** — run `_scripts/file_vuln_issues.py --dry-run`
> to preview it. `tests/test_scripts.py::TestFindingCoverageMatchesSecurityDoc` fails if the
> findings documented here and the issues this repo can file ever diverge.
>
> **Responsible disclosure:** These are platform-level concerns. We are documenting them here
> to invite mitigation and community discussion. Do not use the automation patterns described
> here to farm achievements on accounts you don't own.
>
> **These are not security vulnerabilities in the bounty sense.** None of them affect the
> confidentiality, integrity, or availability of GitHub systems or user data. They are
> threshold-misalignment and abuse-vector observations. See
> [VULN-007's "Why this is not a HackerOne submission"](#why-this-is-not-a-hackerone-submission)
> and the [retraction in the Disclosure Timeline](#disclosure-timeline).

---

## Table of Contents

1. [Vulnerability Index](#vulnerability-index)
2. [Background](#background)
3. [VULN-001: Quickdraw — Sub-5-Minute Issue/PR Close Loop](#vuln-001-quickdraw--sub-5-minute-issuepr-close-loop)
4. [VULN-002: YOLO — Review-Free Merge via Admin Override](#vuln-002-yolo--review-free-merge-via-admin-override)
5. [VULN-003: Heart On Your Sleeve — Mass Reaction Automation](#vuln-003-heart-on-your-sleeve--mass-reaction-automation)
6. [VULN-004: Pair Extraordinaire — Co-Author Trailer Abuse](#vuln-004-pair-extraordinaire--co-author-trailer-abuse)
7. [VULN-005: Pull Shark — Automated PR Farming](#vuln-005-pull-shark--automated-pr-farming)
8. [VULN-006: Galaxy Brain — Self-Answer Abuse (RETRACTED)](#vuln-006-galaxy-brain--self-answer-abuse-retracted-as-invalid-2026-10-03)
9. [VULN-007: Open Sourcerer — Third-Party PR Spam as an Achievement Path](#vuln-007-open-sourcerer--third-party-pr-spam-as-an-achievement-path)
10. [Achievements assessed and found not exploitable](#achievements-assessed-and-found-not-exploitable)
11. [Proposed Defenses](#proposed-defenses)
12. [Disclosure Timeline](#disclosure-timeline)

---

## Vulnerability Index

| ID | Achievement | Severity | Automation Difficulty | Exploitability |
|---|---|---|---|---|
| VULN-001 | Quickdraw | **Medium** | Trivial | Anyone with repo access |
| VULN-002 | YOLO | **Low** | Trivial | Admin-only |
| VULN-003 | Heart On Your Sleeve | **Low** | Trivial | Any account with reactions access |
| VULN-004 | Pair Extraordinaire | **Low** | Easy | Requires one real collaborator |
| VULN-005 | Pull Shark | **Low** | Easy | Any account with push access |
| VULN-006 | Galaxy Brain | **Retracted** | N/A | **Not exploitable** — requires a different account to accept; already enforced |
| VULN-007 | Open Sourcerer | **Low** | Medium | Third-party PR spam; review is the rate limit |

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

## VULN-006: Galaxy Brain — Self-Answer Abuse (RETRACTED as invalid, 2026-10-03)

**Achievement:** 🧠 Galaxy Brain (`galaxy-brain`)
**Severity:** None — the described vector does not exist.
**Status: RETRACTED.** We tested our own claim and it is false. This entry is kept
visible rather than deleted, because a disclosure document that quietly removes
its mistakes is not a disclosure document.

### What we originally claimed

That Galaxy Brain could be farmed by asking a question, answering it yourself,
and accepting your own answer as repo admin — "repeating until the badge tier is
reached". We proposed mitigations D1 (25% weight for self-answers), D2, D3 and D4.

### What actually happens

**GitHub already requires the acceptance to come from a different account.** D4
is not a suggestion for the future; it is the shipped behaviour, at 0% rather
than 25%.

Direct experiment on 2026-10-03. Two Q&A discussions were created in
`neohiro/achievement-hacks` following our own recipe exactly:

| Field | `#7` | `#19` |
|---|---|---|
| Category | Q&A | Q&A |
| `isAnswered` | true | true |
| `answerChosenAt` | 2026-10-03T17:40:08Z | 2026-10-03T17:43:27Z |
| Asker | `neohiro` | `neohiro` |
| Accepted-answer author | `neohiro` | `neohiro` |

Every documented condition was satisfied, including the Default threshold of two
accepted answers. Roughly four hours later the badge was absent. A scan of all 16
discussion-enabled `neohiro` repositories found 9 discussions and exactly these 2
accepted Q&A answers, so no qualifying answer existed elsewhere.

Corroboration:

- *"you CAN NOT mark your own answers to your own questions. They have to be
  marked by another user."* — orgs/community #27808
- *"Self-marked answers do not count to prevent abuse."* — orgs/community #18384
- *"Keep in mind that discussions must be on public repositories, and self-marked
  answers don't count."* — orgs/community #143321

### Why GitHub hardened it

GitHub's Community staff, describing the change:

> "they had to change the rules of the Galaxy Brain achievement so that Q&A in
> community discussions didn't count towards the achievement, because some users
> started spamming discussions by making questions with secondary accounts and
> answering with the main one" — orgs/community #150697

The abuse we thought we had found is the abuse they had already found and closed.
They went further than we proposed and disabled achievements in `orgs/community`
outright.

### What remains

The only residual vector is **two-account coordination**: one account asks, the
other answers and accepts, on content neither genuinely cares about. That is
ordinary coordinated inauthenticity, indistinguishable from other spam at the
platform level, and not specific to this badge. We are not filing it as a
distinct finding.

One genuine documentation gap survives: **GitHub does not publish the tier
table** (2/8/16/32, community-reported) nor state the different-accepter rule
anywhere in the achievement documentation. Contributors cannot tell what they are
working toward. That is tracked as **G4**, not as a vulnerability.

### Corrected impact

- Self-answered FAQs are a legitimate and common way to write documentation, and
  they are **not** a badge-farming vector.
- Galaxy Brain is the one achievement in this catalog that **cannot** be
  self-served, because closing the loop requires a second person. No script can
  satisfy it.
- Our original entry asserted a false capability and would have wasted the
  reader's time exactly as it wasted ours.

### Corrected recommendation

None. The defences are already implemented. Issue
[#6](https://github.com/neohiro/achievement-hacks/issues/6) was filed from the
false claim and should be read as retracted; a maintainer comment saying so is
the appropriate remedy.

### References

- Corrected guidance: [`_achievements/galaxy-brain/README.md`](./_achievements/galaxy-brain/README.md)
- Original issue (superseded): [#6](https://github.com/neohiro/achievement-hacks/issues/6)
- orgs/community #27808, #18384, #143321, #150697

---

## VULN-007: Open Sourcerer — Third-Party PR Spam as an Achievement Path

**Achievement:** 🌱 Open Sourcerer (`open-sourcerer`)
**Status:** Documented 2026-10-03. Not filed as a bounty report — see "Why this is not a HackerOne submission" below.

### Description

Open Sourcerer is awarded for having code merged into a public repository you do
not own. It is the only achievement in the catalog whose earn condition
**inherently requires action against a third party's account**. Every other
badge can be earned entirely on infrastructure you control.

The interesting property is not that the badge is easy to automate — opening a
pull request is a first-class, documented API operation. The interesting property
is that **the badge's reward condition overlaps with behavior GitHub's spam
policy prohibits**. The same pull request can be:

- accepted, merged, and worth an achievement tier, or
- closed as spam, and cost the submitting account its ability to contribute.

An account can therefore hold Open Sourcerer while simultaneously being banned
from opening pull requests. The badge and the Terms of Service disagree about
what the same action means.

### Severity

Low as a security matter. No data exposure, no privilege escalation, no system
compromise. It is a platform-integrity and moderation-consistency issue.

This is stated plainly because inflating it would undermine the six findings
that came before it.

### Automation difficulty

Medium. Unlike VULN-001 or VULN-005, the loop cannot be closed by the attacker
alone — a maintainer has to review and merge. That review is the natural rate
limit, and it is why this vector is rated lower than Quickdraw despite having
similar scripting ease.

The realistic abuse pattern is low-volume, high-targeting: a large number of
plausible-looking trivial PRs against many small projects that have no branch
protection and an absent maintainer. Success is probabilistic rather than
guaranteed, which caps its value to an attacker.

### Impact

- Open Sourcerer is the badge most likely to be seen on spam-banned accounts, because surviving a
  spam wave is exactly what the tier thresholds reward.
- Tier thresholds are unpublished, so contributors cannot tell whether a genuine
  first contribution is enough. (Also tracked as G4.)
- Maintainers of small projects bear the moderation cost; the account doing the
  farming bears none.

### Proposed Defenses

1. **Exclude spam-flagged activity:** Do not count pull requests from contributions later marked
   spam by the receiving repository, or from accounts subsequently suspended for abuse. The signal
   already exists; the badge just ignores it.
2. **Publish tier thresholds:** Disclose the counts. Currently contributors are guessing.
3. **Decay over time:** Weight older contributions less, so a badge cannot be built once and
   displayed indefinitely.
4. **Single-tier on first contribution:** Reserve higher tiers for accounts with a sustained,
   multi-repo contribution history, so the badge rewards breadth over volume.

### Why this is not a HackerOne submission

The six earlier findings were filed as issues on this repository, and the
disclosure timeline below carries the note "GitHub Security team notified via
HackerOne GitHub Bug Bounty (if applicable)". That caveat was doing too much work.

**GitHub's bug bounty program pays for vulnerabilities that compromise
confidentiality, integrity, or availability of GitHub's systems or users'
data.** None of VULN-001 through VULN-007 do. They are threshold-misalignment
and abuse-vector observations. Submitting them to a security bounty is a category
error, and a researcher who does it repeatedly becomes the kind of noise that
gets legitimate reports deprioritized.

The correct channels for this class of report are GitHub Support, the
`github/roadmap` and `github-community` discussions, or a direct engineering
contact — not the security bounty queue.

This document is therefore best read as **an engineering-priority argument**,
which is also why every finding proposes specific, implementable mitigations.

### References

- [`_achievements/open-sourcerer/README.md`](./_achievements/open-sourcerer/README.md)
- [`_docs/AUTOMATION_ETHICS.md`](./_docs/AUTOMATION_ETHICS.md)
- GitHub Acceptable Use Policies — <https://docs.github.com/en/site-policy/acceptable-use-policies>

---

## Achievements assessed and found not exploitable

For completeness, the remaining catalog entries were reviewed and are **not**
filed as findings:

| Achievement | Why no finding |
|---|---|
| ⭐ Starstruck | Stars are social proof from independent accounts. There is no vector that produces stars without a human choosing to press one. Automating the *promotion* of a repo is legitimate marketing, not an exploit. |
| 💖 Public Sponsor | Requires real money through GitHub Sponsors. Not automatable in any meaningful sense. |

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
| **G6** | **Exclude sanctioned activity:** Do not count contributions later marked as spam, or made by accounts subsequently suspended for abuse. The enforcement signal already exists; the badge layer ignores it. | VULN-007 | Trivial |

### Privacy Note

All proposed defenses respect user privacy. None of the above defenses require inspecting private repositories or exposing user behavior data. They operate on public signals: account age, public PR/issue count, public star counts, and public reaction activity.

---

## Disclosure Timeline

| Date | Event |
|---|---|
| 2026-08-31 | VULN-001 through VULN-006 documented in `neohiro/achievement-hacks` |
| 2026-08-31 | Filed as GitHub Issues [#1](https://github.com/neohiro/achievement-hacks/issues/1) through [#6](https://github.com/neohiro/achievement-hacks/issues/6) |
| 2026-08-31 | Disclosure timeline originally recorded "GitHub Security team notified via HackerOne (if applicable)". **Retracted 2026-10-03** — see below. |
| 2026-10-03 | VULN-007 (Open Sourcerer) documented; Starstruck and Public Sponsor assessed and found not exploitable |
| 2026-10-03 | Catalog statuses reconciled against the live profile; 3 of 9 were stale (`pull-shark`, `starstruck`, `yolo` were already earned) |
| 2026-10-03 | `_docs/AUTOMATION_ETHICS.md` and `_docs/VERIFICATION.md` written; `grant_all.py` removed from the advertised structure |
| TBD | GitHub acknowledges / implements defenses |
| TBD | This document updated with resolution status |

### Retraction: the HackerOne note

The 2026-08-31 entry claimed the GitHub Security team was notified through
HackerOne. That claim is **retracted** because it should never have been made.

GitHub's bounty program scopes to vulnerabilities affecting the confidentiality,
integrity, or availability of GitHub systems or user data. None of these
findings do; they are product-abuse and threshold-design observations. Filing
them to a security bounty would not have produced a payout, and would have
misrepresented this work as security research in the channel where that
distinction carries weight.

No HackerOne report was submitted for VULN-001 through VULN-006, and none will be
submitted for VULN-007. The correct route for this class of finding is GitHub
Support or the public `github/roadmap` and `github-community` discussions. The
timeline keeps the retraction visible rather than quietly deleting the row.

---

## License

This security disclosure is published under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The automation scripts described in this document are for **research and defense purposes only**.
Do not use them to farm achievements on accounts you don't own. Such use likely violates GitHub's Terms of Service.
