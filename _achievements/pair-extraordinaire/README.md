# 👥 Pair Extraordinaire

> **Status: `Earned`** — PR #8 merged on 2026-08-31 with a co-authored commit. ✅

## What it measures

You used GitHub's **co-author attribution** (`Co-authored-By:` trailer in a commit message) on a commit that landed in a **merged pull request**.

## Visual

Two overlapping user silhouettes or code brackets. The aesthetic is collaborative — blue/teal tones.

- Bronze → Silver → Gold: more elaborate/complex animation

## Tiers

| Tier | Co-authored commits on merged PRs |
|---|---|
| Default | 1 |
| Bronze | 10 |
| Silver | 24 |
| Gold | 48 |

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

✅ Earned via PR #8 "co-authored commit automation" on 2026-08-31. Tiers will now accumulate with each additional qualifying merged PR.

## Difficulty assessment

**Trivial** — Was earned in one PR merge with one real co-author account. Subsequent tiers (Bronze/Silver/Gold) require accumulating additional co-authored merged commits.
