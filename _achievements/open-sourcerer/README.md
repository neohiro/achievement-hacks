# 🌱 Open Sourcerer

> **Status: `Not yet`** — requires merged contribution to a public repo neohiro does not own.

## What it measures

You got a **commit (or PR) merged into a public repository you don't own**. The first time this happens, you earn the badge.

## Visual

Open-source code symbol (brackets `< >`) with a globe and a seedling. Green tones — growth metaphor.

## Tiers

| Tier | Required |
|---|---|
| Default | 1 |
| Bronze | Unknown |
| Silver | Unknown |
| Gold | Unknown |

GitHub has not published tier thresholds. Some accounts hit Gold by contributing tiny typo/dependency fixes to hundreds of popular repos.

## How it works

1. Find a public repo (not owned by you).
2. Make a useful contribution (PR or commit on a fork).
3. Get it merged.
4. The badge appears.

This is the most **honest** of the activity-based achievements. Real open-source contributions are the path.

## Automated recipe

**There is no honest automated recipe.** You could:
- Find typos across hundreds of popular repos → fix → PR → merge.
- Update dependencies across popular repos.
- Fix issues tagged `good first issue`.

But these are essentially the same actions a real open-source contributor would take, just with optimized targeting.

```bash
#!/usr/bin/env bash
# earn_open_sourcerer.sh — informational
# The fastest *honest* path:

# 1. Find a popular repo with open good-first-issues
gh search issues 'is:open is:issue label:"good first issue" repo:python/cpython' --limit 10

# 2. Fork it, fix one, open a PR
# 3. Wait for the maintainer to merge
# 4. Repeat for one merge — Default earned
```

## Manual recipe

1. **Pick a project you actually use.** Your contribution will be more authentic and mergeable.
2. **Look for `good first issue` labels.** Maintainers use these to flag newcomer-friendly work.
3. **Read the contributing guide** before opening a PR. Skipping this is the #1 reason PRs are rejected.
4. **Make a small, focused change.** Don't try to refactor the world in your first PR.
5. **Be patient with reviews.** Maintainers are often volunteers.
6. **One merged PR = Default earned.** Then keep going if you want Bronze/Silver/Gold.

## neohiro status

- Not yet started.
- Good targets: any project the org already uses (tailscale, age, structlog, github actions ecosystem, etc.)
- Realistic target: contribute to 1 popular repo per quarter

## Difficulty assessment

**Hard** for the spirit, **Trivial** for the letter.

A single typo-fix merged into a mega-popular repo earns Default. But the *intent* of the achievement is to recognize **real open source participation**, and the best path is to actually contribute meaningfully. Tier thresholds being unpublished is GitHub's way of saying "earn it the honest way and we'll recognize you."
