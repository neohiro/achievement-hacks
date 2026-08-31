# 🔫 Quickdraw

> **Status: `Earned`** — neohiro opened + closed issue #11 on `ExploitProtection` within 5 minutes on 2026-08-31.

## What it measures

You closed a **GitHub issue or pull request** within **5 minutes** of opening it.

## Visual

A gun-holster / crossdraw icon in red/orange. The profile animation shows the gun being drawn and holstered. Skin-tone variants available.

- Single tier, single badge. No progression.

## Tiers

| Tier | Required |
|---|---|
| Default | 1 (one-time) |

## How it works

1. Open a public issue or PR.
2. Within 5 minutes, **close** it (with any state reason).
3. The badge appears almost immediately.
4. Both the **opener** and the **closer** of the issue can earn the badge if both actions happen within 5 minutes.

## Automated recipe (this is the truest trivial earn)

```bash
#!/usr/bin/env bash
# earn_quickdraw.sh
# Usage: bash earn_quickdraw.sh [repo]
REPO="${1:-neohiro/ExploitProtection}"

echo "=== Earning Quickdraw on $REPO ==="
RESULT=$(gh issue create \
  --repo "$REPO" \
  --title "chore: quickdraw-test $(date +%s)" \
  --body "Closing immediately for Quickdraw achievement." 2>&1)
echo "Opened: $RESULT"
ISSUE_URL=$(echo "$RESULT" | grep -oE 'https://[^ ]+')
ISSUE_NUM=$(echo "$ISSUE_URL" | grep -oE '/[0-9]+$')

# Close within 5 minutes
sleep 1
gh issue close "$ISSUE_NUM" --repo "$REPO" --reason "completed"

echo "✓ Quickdraw earned! (if under 5 min)"
```

Or in PowerShell:
```powershell
$headers = @{Authorization = "Bearer $(gh auth token)"}
$body = @{title = "chore: quickdraw-test"; body = "Closing immediately."} | ConvertTo-Json
$issue = Invoke-RestMethod "https://api.github.com/repos/$repo/issues" -Headers $headers -Method POST -Body $body -ContentType "application/json"
$start = Get-Date
Invoke-RestMethod "https://api.github.com/repos/$repo/issues/$($issue.number)" -Headers $headers -Method PATCH -Body '{"state":"closed","state_reason":"completed"}' -ContentType "application/json" | Out-Null
Write-Host "Closed in $(([Math]::Round(((Get-Date) - $start).TotalSeconds, 2)))s"
```

## Manual recipe

1. Open any issue on a public repo you own.
2. Immediately close it.
3. Done.

## neohiro status

- **Earned on 2026-08-31** — issue #11 on `neohiro/ExploitProtection` opened and closed in <1 second.

## Difficulty assessment

**Trivial** — The badge description is literally "close within 5 minutes." The easiest achievement to earn.
