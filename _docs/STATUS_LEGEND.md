# Status Legend

Every achievement in this repo carries a `status` field in its `meta.yaml` and a badge in its `README.md`.

## Status values

| Status | Meaning |
|---|---|
| `Not yet` | We have documented the achievement, written the recipe, and (usually) written the automation script. No account in the neohiro org has verified receiving it yet. |
| `In progress` | Someone in the org is actively working toward this achievement. The recipe has been started (e.g., Discussions enabled, first co-authored PR merged, etc.). |
| `Earned` | Verified on the neohiro account. The verification date and source are recorded in `meta.yaml`. |
| `Deprecated` | GitHub no longer issues this badge. It still displays on accounts that earned it; no new accounts can receive it. Frozen achievements (Arctic Code Vault, Mars 2020) fall here. |
| `Unobtainable` | Requires enrollment in a program that only GitHub can grant (e.g., Security Bug Bounty Hunter, GitHub Campus Expert). Not achievable by activity alone. |

## Status transition logic

```
Not yet  →  In progress  →  Earned
                ↓
            Deprecated / Unobtainable
```

No achievement ever moves backward.
