# 🦈 Pull Shark

> **Status: `Not yet`** — neohiro has 30+ merged PRs in flagship repos but total is likely below the Default threshold of 2.

## What it measures

The total number of **merged pull requests** across all repositories you have push access to (public **and** private). Every merged PR = 1 toward the counter, regardless of repo.

## Visual

A **shark fin** slicing through blue/purple water. The profile animation shows the fin rising out of the ocean and diving back. Skin tone does not apply to the fin.

- Default → Bronze → Silver → Gold: the fin gets more elaborate/motion-rich

## Tiers

| Tier | Merged PRs required | Badge |
|---|---|---|
| Default | 2 | 🦈 |
| Bronze | 16 | 🦈 (bronze tint) |
| Silver | 128 | 🦈 (silver) |
| Gold | 1024 | 🦈 (gold) |

## How it works

- Only **merged** PRs count. Closed without merging = no credit.
- PRs from **all repos** you have push access to count, including private repos.
- Draft PRs count if they are merged.
- You can earn this across multiple accounts if you have multiple GitHub accounts.

## Automated recipe

The simplest automated path is just to **keep shipping**. Each merged PR on any neohiro repo advances the counter.

```bash
#!/usr/bin/env bash
# earn_pull_shark.sh — count merged PRs for an account across all repos
ACCOUNT="${1:-neohiro}"
TOTAL=0

for repo in $(gh api users/$ACCOUNT/repos --paginate --jq '.[].name'); do
  COUNT=$(gh api repos/$ACCOUNT/$repo/pulls --state closed --paginate --jq '[.[] | select(.merged_at != null)] | length' 2>/dev/null || echo 0)
  TOTAL=$((TOTAL + COUNT))
done

echo "Total merged PRs for $ACCOUNT: $TOTAL / 2 (Default) / 16 / 128 / 1024"
[ "$TOTAL" -ge 2 ] && echo "✓ Pull Shark Default should be earned!" || echo "Need $((2 - TOTAL)) more merged PRs"
```

## Manual recipe

1. Work on anything in any repo you have push access to.
2. Open a PR when you have a change.
3. Get it reviewed and merged.
4. Repeat. The badge will eventually appear.
5. Every merged PR on `ExploitProtection`, `dnscrypt-proxy-gui`, `linux`, `ubuntu`, `windows` counts toward neohiro's total.

## neohiro status

- `ExploitProtection`: 4 merged
- `dnscrypt-proxy-gui`: 15 merged
- `linux`: 4 merged
- `ubuntu`: 3 merged
- `windows`: 3 merged
- Other repos: partial
- **Total known: 30+** — likely past Default (2) and past Bronze (16). Verification pending.

## Difficulty assessment

**Easy** — Just keep merging PRs. Any active org will hit Default (2) within a few weeks of real work.
