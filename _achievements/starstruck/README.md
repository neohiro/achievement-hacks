# ⭐ Starstruck

> **Status: `Not yet`** — neohiro/ExploitProtection has 85 stars, past Default (16) but the badge isn't appearing yet. Verification pending.

## What it measures

You authored a **single** repository that accumulated a given number of ⭐ stars. Only your **highest-starred repository at any moment** counts — so the badge level is driven by your biggest hit, not your total.

## Visual

A **waving hand** emoji (👋) in your skin-tone preference, layered over a star burst. Skin tone is set in `Settings → Appearance → Emoji skin tone preference`.

- Default: yellow tone + gold
- Bronze: warm brown
- Silver: silver-blue
- Gold: bright gold/yellow

## Tiers

| Tier | Stars required | Badge |
|---|---|---|
| Default | 16 | 👋⭐ |
| Bronze | 128 | 👋⭐ (bronze) |
| Silver | 512 | 👋⭐ (silver) |
| Gold | 4096 | 👋⭐ (gold) |

## How it works

- Only your **own** repositories count. You can't Starstruck from contributing to someone else's repo.
- The badge level is determined by **the single repo you own with the most stars**.
- Stars you place on your own repos do not count.
- Stars from a deleted user account still count historically, I believe (unconfirmed by GitHub).

## Automated recipe

There is **no deterministic automation** for this one. Stars are social proof; the only recipe is to ship something that people want to star. However, you can **maximize your signal**:

```bash
# 1. Find your current highest-starred repo
gh api user --jq '.login' | xargs -I{} gh api users/{}/repos --paginate \
  --jq '.[] | select(.stargazers_count > 0) | {name: .name, stars: .stargazers_count}' \
  | sort -k2 -n -r | head -5
```

```bash
# 2. Add a top-line badge + screenshot to the README of your best repo
# (Humans star what they can see. README = homepage.)
```

```bash
# 3. Cross-link from every other repo of yours
# A simple "Made by [@neohiro](https://github.com/neohiro) — see also [neohiro/your-best-repo](...)"
# doubles as a soft funnel.
```

## Manual recipe (the honest path)

1. Pick a problem you actually solve.
2. Build the smallest useful version of the solution.
3. Write a README that explains:
   - **What** it does (1 sentence)
   - **Why** it exists (the pain)
   - **How to install** (a one-liner)
   - **A demo screenshot or GIF** (this is non-negotiable — visual proof triples star rates)
4. Post it on:
   - Hacker News (`Show HN:`)
   - relevant subreddits (`r/programming`, `r/opensource`, `r/sysadmin`, `r/privacy`, etc.)
   - dev.to, hashnode
   - relevant Discord servers
5. Reply to **every issue** opened in the first month. Stars follow engagement.
6. Don't delete and re-push the repo — that resets stars to 0 in some old accounts' histories.

## Difficulty assessment

**Medium** — Trivially mechanical at low counts (16 stars can come from 16 friends, GitHub won't tell you not to). Realistically, getting to Bronze (128) requires one of:
- A genuinely useful tool
- A viral moment
- Years of consistent small wins

## neohiro status

- `ExploitProtection` has **85 stars** — past Default (16) ✓
- Should already be showing the **Default** badge. If not, check `Settings → Public profile → Display achievements on my profile`.
- Bronze (128) is **43 stars away** — closest target.
- Realistic Bronze ETA: 6–12 months of organic growth.

## Community

- [drknzz/GitHub-Achievements](https://github.com/drknzz/GitHub-Achievements) — community badge visual catalog
- [GitHub's official docs](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-github-profile/customizing-your-profile/personalizing-your-profile#displaying-badges-on-your-profile)
