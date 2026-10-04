# Status Legend

Every achievement in this repo carries a `status` field in its `meta.yaml` and a badge in its `README.md`.

## Status values

| Status | Meaning |
|---|---|
| `Not yet` | We have documented the achievement, written the recipe, and (usually) written the automation script. No account in the neohiro org has verified receiving it yet. |
| `In progress` | Someone in the org is actively working toward this achievement. The recipe has been started (e.g., Discussions enabled, first co-authored PR merged, etc.). |
| `Earned` | Verified on the neohiro account. **Requires a `verified:` block in `meta.yaml`** recording the tier, date, and the artefact observed. |
| `Deprecated` | GitHub no longer issues this badge. It still displays on accounts that earned it; no new accounts can receive it. Frozen achievements (Arctic Code Vault, Mars 2020) fall here. |
| `Unobtainable` | Requires enrollment in a program that only GitHub can grant (e.g., Security Bug Bounty Hunter, GitHub Campus Expert). Not achievable by activity alone. |

## Values are exact, and machine-checked

`status` must be one of the five strings above, spelled exactly —
`Earned`, not `earned`. `_scripts/grant_check.py` parses it as an anchored
top-level scalar without PyYAML, and an unrecognised value is reported as
`malformed` and fails the audit rather than being treated as `Not yet`. A silent
case-mismatch is exactly how this catalog rotted in the first place.

The same applies to `earnable`, which must be `true` or `false`.

## `Earned` requires evidence

An `Earned` status with no `verified:` block is a claim, not a record.
`tests/test_scripts.py::TestRealCatalog` fails if any `Earned` entry lacks one,
and the block's shape is specified in
[`ACHIEVEMENT_FORMAT.md`](./ACHIEVEMENT_FORMAT.md).

## Status transition logic

```
Not yet  →  In progress  →  Earned
                ↓
            Deprecated / Unobtainable
```

No achievement ever moves backward.

## Verification

Status is not maintained by hand. See [`VERIFICATION.md`](./VERIFICATION.md) for
how each value is checked against the live profile, and
[`grant_check.py`](../_scripts/grant_check.py) for the command:

```bash
python _scripts/grant_check.py --account neohiro   # exit 2 on any disagreement
```
