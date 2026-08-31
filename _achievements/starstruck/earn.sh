#!/usr/bin/env bash
# earn_starstruck.sh — Check star counts for all neohiro repos
# Usage: bash earn_starstruck.sh [account]
set -euo pipefail

ACCOUNT="${1:-neohiro}"
REPO="ExploitProtection"  # the known flagship

echo "=== Starstruck check for $ACCOUNT ==="
echo "Target: ExploitProtection"
STARS=$(gh api repos/$ACCOUNT/$REPO --jq '.stargazers_count')
echo "Stars: $STARS / 16 (Default) / 128 (Bronze) / 512 (Silver) / 4096 (Gold)"

if [ "$STARS" -ge 16 ]; then
  echo "✓ Default Starstruck should be EARNED"
else
  echo "✗ Not yet — need $((16 - STARS)) more stars"
fi
if [ "$STARS" -ge 128 ]; then
  echo "✓ Bronze earned"
elif [ "$STARS" -ge 16 ]; then
  echo "  Bronze: need $((128 - STARS)) more"
fi

echo ""
echo "Top 5 starred repos for $ACCOUNT:"
gh api repos/$ACCOUNT --paginate --jq '.[] | select(.stargazers_count > 0) | "\(.name): \(.stargazers_count)"' 2>/dev/null | sort -t: -k2 -n -r | head -5
