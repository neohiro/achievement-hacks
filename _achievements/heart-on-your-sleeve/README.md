# ❤️ Heart On Your Sleeve

> **Status: `Not yet`** — requires a ❤️ reaction on a comment or discussion.

## What it measures

You added a **heart reaction (❤️)** to a comment, issue, or discussion. The heart is the standard GitHub reaction emoji — `+1`, `hooray`, etc. do not count.

## Visual

A heart on a sleeve/clothing element. Red/pink tones. The profile animation shows a heart stitching onto fabric.

## Tiers

| Tier | Required | Evidence |
|---|---|---|
| Default | 1 | community-reported |
| Bronze | Unknown | Unpublished |
| Silver | Unknown | Unpublished |
| Gold | Unknown | Unpublished |

GitHub has not published the tier thresholds for this achievement.

## How it works

1. Go to any comment, issue, PR, or discussion.
2. Click the reaction button.
3. Select ❤️.
4. Done. Counter increments.

## Automated recipe

**Note: Automated reactions are against GitHub ToS.** The script below is for **documentation purposes only** — we include it so you understand the mechanic, not to encourage mass-reacting.

```bash
#!/usr/bin/env bash
# earn_heart_on_your_sleeve.sh — INFORMATIONAL ONLY
# Automating reactions violates GitHub ToS.
# Use this only to understand the mechanic.

REPO="neohiro/achievement-hacks"
ISSUE_NUM=1

# Get the comment ID
COMMENT_ID=$(gh api repos/$REPO/issues/comments \
  --jq '.[0].id' 2>/dev/null)

# Add heart reaction (requires manual browser interaction or OAuth with full repo scope)
echo "To earn this, react manually: go to any comment → click 😊 → select ❤️"
echo "This is the most trivially gameable badge — worth 1 heart reaction."
```

**The honest manual path:**
1. While reviewing issues and PRs, if a comment resonates — react with ❤️.
2. Set a personal rule: react with ❤️ to any comment that makes you smile.
3. That's it. Natural GitHub usage will push you past Default quickly.

## Manual recipe

1. Open any comment on any GitHub issue, PR, or discussion (public repos).
2. Click the reaction icon (😊).
3. Select ❤️.
4. Repeat naturally.

## neohiro status

- Not yet started. Requires manual interaction.
- Re-check at any time with `python _scripts/grant_check.py`.

## Difficulty assessment

**Trivial** — if you're manually active. The only barrier is remembering to do it. If you're active on GitHub 10+ minutes a day, you'll earn this within a week passively.

## ⚠️ Ethics note

Automated mass-reactions are trivially detectable by GitHub and likely violate the ToS. The spirit of the achievement is to react to things you genuinely care about. Use it as intended.

Concretely: the documented automation for this badge ([`SECURITY.md` VULN-003](../../SECURITY.md)) iterates over *scraped* comment URLs belonging to strangers and fires reactions at each one. That is not engagement, it is notification spam directed at people who never asked for it, and no badge is worth that. Reacting to comments you have actually read needs no automation and is not what this note is about.

There is deliberately no script in this repo for earning this badge.

See [`_docs/AUTOMATION_ETHICS.md`](../../_docs/AUTOMATION_ETHICS.md).
