# 🧠 Galaxy Brain

> **Status: `In progress`** — Discussions enabled on `neohiro/Heart`, `neohiro/neohiro.github.io`, `neohiro/worldmap`, `neohiro/opencode`, `neohiro/mobile-sync`. First accepted answer pending.

## What it measures

You had a **GitHub Discussion answer marked as "Accepted"** in a Q&A category. Each accepted answer = 1 toward the counter.

## Visual

A spiral galaxy inside a brain icon, purple/blue nebula tones. Tiers increase the spiral complexity and the brightness of the nebula.

## Tiers

| Tier | Accepted answers |
|---|---|
| Default | 2 |
| Bronze | 8 |
| Silver | 16 |
| Gold | 32 |

## How it works

1. Repo must have **GitHub Discussions enabled** (not all repos do).
2. There must be a **Q&A** category. Open-ended discussions don't count.
3. Someone asks a question, you post an answer, the question asker (or an admin) marks it **Accepted**.
4. You can also **self-Q&A**: ask a question, answer it, and mark your answer accepted (the bot auto-marks the first reply in some setups).

## Automated recipe

This is the **hardest** of the trivially-earnable achievements because:
- Discussions must be enabled
- The asker must mark the answer accepted (or you must self-ask, which has a cooldown for some accounts)

The fastest path:

```bash
#!/usr/bin/env bash
# earn_galaxy_brain.sh
# Step 1: Enable Discussions on a public repo
REPO="${1:-neohiro/Heart}"
gh api repos/$REPO -X PATCH -f has_discussions=true | jq '.has_discussions'

# Step 2: Seed a Q&A discussion (via the GraphQL API, requires admin token)
# See _scripts/seed_discussion.py
```

The **deterministic workflow** for the org:
1. Enable Discussions on a public repo (already done for several).
2. Create a Q&A category if missing.
3. **Self-ask a question** like "How do I deploy this?"
4. **Answer it yourself** as the repo admin.
5. **Mark your answer as accepted** as the asker.
6. Repeat twice. → Default.

## Manual recipe

1. Open the Discussions tab on `neohiro/Heart`.
2. Post a Q&A question: "How do I configure X?" or "What's the recommended setup for Y?"
3. As the repo owner, you can self-answer.
4. Mark your own answer accepted.
5. Have a friend ask a real question in the same Q&A category.
6. Answer it. Have them mark it accepted.
7. Repeat 2–32 times depending on tier target.

## neohiro status

- Discussions enabled on: `Heart`, `neohiro.github.io`, `worldmap`, `opencode`, `mobile-sync`, `ExploitProtection`, `dnscrypt-proxy-gui`, `BlackGlass`, `Cripple-NetStrip`, `linux`, `ubuntu`, `windows`, `auto-resume` (13 repos)
- Need to seed Q&A category + first accepted answer
- Target: Default (2) by end of week

## Difficulty assessment

**Medium** — Mechanically straightforward, but requires the Discussions + Q&A category + accepted answer flow, which is multi-step.
