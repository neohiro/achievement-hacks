# 👥 Pair Extraordinaire

> **Status: `Not yet`** — retracted 2026-10-06; see below.

## What it measures

You used GitHub's **co-author attribution** (`Co-authored-By:` trailer in a commit message) on a commit that landed in a **merged pull request**.

## Visual

Two overlapping user silhouettes or code brackets. The aesthetic is collaborative — blue/teal tones.

- Bronze → Silver → Gold: more elaborate/complex animation

## Tiers

| Tier | Co-authored commits on merged PRs | Evidence |
|---|---|---|
| Default | 1 | community-reported |
| Bronze | 10 | community-reported |
| Silver | 24 | community-reported |
| Gold | 48 | community-reported |

## How it works

1. You need at least **one** real GitHub co-author (another account).
2. You add `Co-authored-by: Name <email@example.com>` to your commit message.
3. The PR must be merged.
4. Every qualifying commit increments your counter.

## Automated recipe

The easiest automated path: add a co-author to every commit going forward. This requires at minimum **one real collaborator account**.

```bash
#!/usr/bin/env bash
# earn_pair_extraordinaire.sh
# Usage: bash earn_pair_extraordinaire.sh <repo> <pr_number> <your_name> <your_email> <coauthor_name> <coauthor_email>

REPO="${1}"
PR="${2}"
YOUR_NAME="${3}"
YOUR_EMAIL="${4}"
COAUTHOR_NAME="${5}"
COAUTHOR_EMAIL="${6}"

# Fetch the PR's head branch
HEAD_BRANCH=$(gh api repos/neohiro/$REPO/pulls/$PR --jq '.head.ref')
gh repo clone neohiro/$REPO /tmp/$REPO -- --depth=1
cd /tmp/$REPO
git checkout $HEAD_BRANCH

# Make a dummy commit with co-author
git commit --allow-empty -m "chore: pair programming attestation

Co-authored-by: $COAUTHOR_NAME <$COAUTHOR_EMAIL>"
git push origin $HEAD_BRANCH

echo "Pushed co-authored commit to $REPO PR #$PR"
echo "Pair Extraordinaire: +1 (after merge)"
```

## Manual recipe

1. Find a PR you want to contribute to.
2. Make sure the PR branch is up to date.
3. When committing, add this to your commit message:

```
Some commit message

Co-authored-by: Their Name <their@email.com>
```

4. Open a PR (or push to an existing PR branch).
5. After merge, you get +1.

**The key habit:** Every time you review someone else's PR and suggest a small fix, instead of commenting — push a commit directly to their branch with your name as co-author. This is good etiquette AND it earns the badge.

## neohiro status

Not yet. This previously read "Earned via PR #8 on 2026-08-31", and that claim has
been retracted — see the retraction note below.

Re-check at any time with `python _scripts/grant_check.py --account neohiro`.

### Retraction, 2026-10-06

This entry asserted `status: Earned` on the strength of merged PR #8. That was
an inference, not a measurement: it read "the PR has a qualifying co-authored
commit, therefore the badge exists". The four badges neohiro genuinely holds each
cite the badge asset rendered on the live profile sidebar, which is a different
kind of evidence.

`grant_check.py` compared the catalog against the live profile on 2026-10-06 and
found four badges — pull-shark, quickdraw, starstruck, yolo — with this one
absent. The recipe below is still believed to work; what is retracted is the
claim that it had been *demonstrated* to work on this account.

This is the same failure mode as [VULN-006](../../SECURITY.md): a claim about a
badge stated as fact when nothing had been measured. The fix there was to record
the retraction. The fix here is the same.

If the badge later does appear on the profile, restore `status: Earned` and put
back a `verified:` block that cites the observed badge asset, not the PR.

## ⚠️ Ethics note

This badge requires **a second human being**. That is a built-in limiter, and it
is worth respecting rather than routing around: the documented automation
([`SECURITY.md` VULN-004](../../SECURITY.md)) creates 50 empty commits carrying a
`Co-authored-by:` trailer to a second account, inflating the counter 50× in one
merge. A trailer asserts that a person contributed; forging it in bulk is a lie
in the commit metadata of someone else's repository, and it is the kind of thing
that makes maintainers distrust co-author attribution generally.

Co-authoring a commit you actually worked on needs no automation.

See [`_docs/AUTOMATION_ETHICS.md`](../../_docs/AUTOMATION_ETHICS.md).

## Difficulty assessment

**Trivial** — one merged PR with one real co-author account is enough for Default. Subsequent tiers (Bronze/Silver/Gold) require accumulating additional co-authored merged commits.
