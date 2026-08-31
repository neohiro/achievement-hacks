# 🏴 YOLO

> **Status: `Not yet`** — branch protection rules on neohiro repos currently require reviews, blocking solo merges.

## What it measures

You merged a **pull request** that received **zero reviews**.

## Visual

A bold YOLO badge with a free-spirited motif. The profile animation is dramatic — the badge flickers and the text "YOLO" appears in graffiti/handwritten style.

- Single tier, single badge. No progression.

## Tiers

| Tier | Required |
|---|---|
| Default | 1 (one-time) |

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

- No neohiro repo is currently configured to allow solo merges on `main`
- The simplest earn target would be a fresh public repo with no branch protection

## Difficulty assessment

**Trivial** — Mechanically a single PR merge. The only friction is the (very reasonable) branch protection rules on real projects.
