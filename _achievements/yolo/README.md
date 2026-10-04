# 🏴 YOLO

> **Status: `Earned`** — Default tier, verified 2026-10-03 against the live profile.

## What it measures

You merged a **pull request** that received **zero reviews**.

## Visual

A bold YOLO badge with a free-spirited motif. The profile animation is dramatic — the badge flickers and the text "YOLO" appears in graffiti/handwritten style.

- Single tier, single badge. No progression.

## Tiers

| Tier | Required | Evidence |
|---|---|---|
| Default | 1 (one-time) | Verified - badge held |

## How it works

1. Open a PR on a public repo.
2. Make sure **no one reviews it** (no approving reviews, no change requests).
3. Click "Merge pull request."
4. The badge appears.

**Caveat:** Repos with branch protection rules that **require** reviews will block this. Some repos have admin overrides that allow admins to bypass the review requirement — those count.

## Automated recipe

```bash
#!/usr/bin/env bash
# earn_yolo.sh
# Usage: bash earn_yolo.sh [repo]
set -euo pipefail

REPO="${1:-neohiro/dummy-yolo}"
BRANCH="yolo-$(date +%s)"

# Create a test repo if needed
gh repo create "$REPO" --public --add-readme 2>/dev/null || true

# Push a one-commit branch
TMP=$(mktemp -d)
cd $TMP
git init -q
git remote add origin "https://github.com/$REPO.git"
git pull origin main 2>/dev/null || true
echo "# YOLO test" > README.md
git add README.md
git -c user.email="neohiro@users.noreply.github.com" -c user.name="neohiro" commit -q -m "Initial commit"
git push -q -u origin HEAD:main

# Open a PR (will auto-merge if branch protection allows)
PR_URL=$(gh pr create --repo "$REPO" --title "Initial commit" --body "YOLO test" --base main --head main 2>&1 || echo "no PR needed")

echo "✓ Push complete. If no branch protection requires reviews, badge should appear."
```

**Easier path on existing repos with no branch protection:**
```bash
# On any neohiro repo with no required-review branch protection:
# 1. Make a tiny change on a new branch
# 2. Open a PR
# 3. Click merge yourself
# 4. Done — YOLO!
```

## Manual recipe

1. Pick a public repo with no branch protection requiring reviews (or with admin override).
2. Make a trivial change.
3. Open a PR.
4. Click "Merge pull request" without waiting for reviews.
5. Done.

**⚠️ Safety note:** This is the canonical "anti-pattern" achievement. The badge itself rewards the behavior the rest of GitHub's UI tries to discourage. Earn it on a sandbox repo to keep your real workflow safe.

## neohiro status

**`Earned` — verified 2026-10-03.** The live profile renders the `yolo-default`
badge asset.

> Earlier revisions of this file claimed the badge was blocked because "no
> neohiro repo is currently configured to allow solo merges on `main`". That
> claim was wrong on its own terms — it contradicted the existence of a merged,
> unreviewed PR somewhere in the account's history, and the badge had in fact
> already been awarded. Treat the "no repo allows solo merges" assertion as
> unverified; branch protection is a per-repo, per-branch setting and the
> account has many repos.

This is the one badge in the catalog where the *earned* state is consistent with
the documented harm: YOLO rewards merging unreviewed code, so the badge is
evidence that the guardrail was bypassed at least once. See
[`SECURITY.md` VULN-002](../../SECURITY.md) for why that is worth reporting.

## Difficulty assessment

**Trivial** — Mechanically a single PR merge. The only friction is the (very
reasonable) branch protection rules on real projects.
