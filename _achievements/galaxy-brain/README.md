# 🧠 Galaxy Brain

> **Status: `In progress`** — blocked on a second person, not on technique.
> Discussions are enabled on 16 repos and two qualifying Q&A threads exist
> (`achievement-hacks` #7 and #19). Both are correctly categorised, both have
> `isAnswered=true`, and both meet the Default threshold of 2. Neither counts
> because **a self-accepted answer does not earn this badge.** See
> [Verified failure](#verified-failure-2026-10-03) below.

## What it measures

You had a **GitHub Discussion answer marked as "Accepted"** in a Q&A category,
where the acceptance was made by **someone other than you**.

## Visual

A spiral galaxy inside a brain icon, purple/blue nebula tones. Tiers increase the spiral complexity and the brightness of the nebula.

## Tiers

| Tier | Accepted answers | Evidence |
|---|---|---|
| Default | 2 | community-reported |
| Bronze | 8 | community-reported |
| Silver | 16 | community-reported |
| Gold | 32 | community-reported |

GitHub does not publish this table. Treat the numbers as community-reported.

## How it works

1. Repo must have **GitHub Discussions enabled** (not all repos do).
2. There must be a **Q&A** category. Announcements, Ideas, Show and Tell, and
   General discussions do not count, even if a reply is accepted.
3. **Someone else asks a question.** You post an answer.
4. **The asker — or a maintainer — marks your answer Accepted.**
5. That is the only route. Two accepted answers earn Default.

### The rule that is easy to get wrong

**You cannot accept your own answer, even as the repository admin.**

This is not documented by GitHub, and an earlier revision of this file claimed
the opposite. It was wrong, and following it wasted real effort. Community
consensus, GitHub's own community team, and one direct experiment all agree:

> "you CAN NOT mark your own answers to your own questions. They have to be
> marked by another user." — orgs/community #27808

> "Self-marked answers do not count to prevent abuse." — orgs/community #18384

GitHub has been explicit about why:

> "they had to change the rules of the Galaxy Brain achievement so that Q&A in
> community discussions didn't count towards the achievement, because some users
> started spamming discussions by making questions with secondary accounts and
> answering with the main one" — orgs/community #150697, GitHub Community staff

The practical consequence: **this badge requires another human being.** It is the
only achievement in this catalog with a hard social requirement rather than a
technical one.

## Automated recipe

**None exists, and none can.** This is the only achievement in the catalog where
that is a property of the badge rather than a gap in our tooling.

The award requires an accepted answer, and GitHub requires the acceptance to come
from a *different account* than the answer author. Closing that loop needs a
second person, so the final step is outside any script's reach — including a
script driving two accounts, which is the coordinated-inauthenticity behaviour
GitHub cited when it hardened the rule.

Verified on 2026-10-03: the closest mechanical approximation (self-ask, self-answer,
self-accept) satisfies every documented condition and awards nothing. See
[Verified failure](#verified-failure-2026-10-03).

An earlier revision of this file claimed a deterministic self-Q&A workflow. It was
wrong; the retraction is in [`SECURITY.md` VULN-006](../../SECURITY.md).

## Manual recipe

1. Find a public repo with Discussions enabled and an active **Q&A** category.
   Repos with real questions from real people are the target — not your own.
2. Answer a question you can genuinely help with.
3. The asker marks your answer Accepted. If they don't, ask politely; do not
   pressure them.
4. Repeat once more for Default.

Check the answer is attributed to the account you want credited before the
acceptance is granted — it is much harder to fix afterwards.

### Anti-pattern: self-Q&A

Ask a question, answer it yourself, accept your own answer. **This does not
work**, and it also litters a repository with content nobody asked for. Two
threads created this way sit in `achievement-hacks` (#7, #19) as evidence.

Note also that achievements **cannot be earned in `orgs/community`** at all;
GitHub disabled them there in response to exactly this kind of gaming.

## Verified failure (2026-10-03)

Direct experiment, since the rule is undocumented and this file previously
asserted the opposite.

| Field | `#7` | `#19` |
|---|---|---|
| Category | Q&A | Q&A |
| `isAnswered` | true | true |
| `answerChosenAt` | 2026-10-03T17:40:08Z | 2026-10-03T17:43:27Z |
| Asker | `neohiro` | `neohiro` |
| Accepted-answer author | `neohiro` | `neohiro` |

All documented conditions were satisfied and the threshold of 2 was met. Roughly
four hours later the badge was still absent from the profile. The only unmet
condition is that the accepter and the answer author were the same account.

A full scan of all 16 discussion-enabled `neohiro` repos found 9 discussions and
exactly these 2 accepted Q&A answers, so there is no qualifying answer hiding in
another repository.

Reproduce the check:

```bash
python _scripts/grant_check.py --account neohiro
```

## neohiro status

- Discussions enabled on 16 repos (verified 2026-10-03 via the GitHub API):
  `achievement-hacks`, `auto-resume`, `BlackGlass`, `Cripple-NetStrip`,
  `dnscrypt-proxy-gui`, `ExploitProtection`, `Heart`, `linux`,
  `meshcore-waveshare-usb-lora`, `meteo-ics`, `mobile-sync`, `neohiro.github.io`,
  `opencode`, `ubuntu`, `windows`, `worldmap`.
  Only `achievement-hacks` and `meteo-ics` currently hold a Q&A discussion.
- Infrastructure is ready. The blocker is that no second person has asked a
  question and accepted an answer.
- Realistic path to Default: answer 2 genuine questions in an active third-party
  Q&A discussion, or ask a collaborator to do so in ours.
- Re-check at any time with `python _scripts/grant_check.py`.

> An earlier revision of this file listed 13 repositories and omitted
> `achievement-hacks` — the repository these two threads actually live in. A
> hand-maintained list of this kind drifts; re-derive it rather than trusting it:

```bash
gh api "users/neohiro/repos?per_page=100" --jq '.[] | select(.has_discussions) | .name'
```

## ⚠️ Ethics note

Answering real questions because you know the answer is the feature working as
designed and needs no automation.

There is deliberately no automation here. Unlike most badges in this catalog,
Galaxy Brain **cannot** be self-served: the acceptance must come from another
person, so no script can close the loop. That is a property GitHub enforces, and
it is the reason this entry is `automatable: false`.

The remaining abuse vector is not self-answering — that is already blocked — but
coordinating a second account to manufacture questions and accept your own
answers. That is the behaviour GitHub cited when it hardened the rules, and it
is not something this repo will help with. See
[`SECURITY.md` VULN-006](../../SECURITY.md), which has been corrected after this
experiment disproved its original claim.

See [`_docs/AUTOMATION_ETHICS.md`](../../_docs/AUTOMATION_ETHICS.md).

## Difficulty assessment

**Hard** — and *socially* hard, which is why it is rated above the other
"Trivial" badges. Every mechanical step is easy and none of them are the
bottleneck. The badge requires two distinct people, so it cannot be closed by
effort alone.
