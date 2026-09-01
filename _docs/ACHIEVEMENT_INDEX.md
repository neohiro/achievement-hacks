# Achievement Index

Canonical, machine-readable list of all GitHub Achievements known to this repo.
The single source of truth is `_achievements/<slug>/meta.yaml`. This file and
`_scripts/list_achievements.py` are both generated from it.

## Achievement list (live)

Run `python _scripts/list_achievements.py` to see the current canonical list.
Last verified on 2026-08-31 against 15 achievement meta.yaml files.

| # | Slug | Name | Tier count | Earnable? | Status |
|---|---|---|---|---|---|
| 1 | `starstruck` | Starstruck | 4 (Default → Gold) | Yes | Not yet |
| 2 | `pull-shark` | Pull Shark | 4 (Default → Gold) | Yes | Not yet |
| 3 | `pair-extraordinaire` | Pair Extraordinaire | 4 (Default → Gold) | Yes | **Earned** ✅ |
| 4 | `galaxy-brain` | Galaxy Brain | 4 (Default → Gold) | Yes | Not yet |
| 5 | `quickdraw` | Quickdraw | 1 | Yes | Not yet |
| 6 | `yolo` | YOLO | 1 | Yes | Not yet |
| 7 | `heart-on-your-sleeve` | Heart On Your Sleeve | 4 (Default → Gold) | Yes | Not yet |
| 8 | `open-sourcerer` | Open Sourcerer | 4 (Default → Gold) | Yes | Not yet |
| 9 | `public-sponsor` | Public Sponsor | 1 | Yes | Not yet |
| 10 | `arctic-code-vault` | Arctic Code Vault Contributor | 1 | **No** (frozen) | Deprecated |
| 11 | `mars-2020` | Mars 2020 Contributor | 1 | **No** (frozen) | Deprecated |

## Highlights (account-tier, not activity-based)

| Slug | Name | Status |
|---|---|---|
| `github-pro` | GitHub Pro | Unobtainable |
| `developer-program-member` | Developer Program Member | Unobtainable |
| `security-bug-bounty-hunter` | Security Bug Bounty Hunter | Unobtainable |
| `github-campus-expert` | GitHub Campus Expert | Unobtainable |
| `security-advisory-credit` | Security Advisory Credit | Unobtainable |

## How to add a new achievement

1. Create `_achievements/<slug>/meta.yaml` matching `ACHIEVEMENT_FORMAT.md`.
2. Create `_achievements/<slug>/README.md` following the template.
3. (Optional) Create `_achievements/<slug>/earn.sh` for an automation recipe.
4. Update the achievement table in this file.
5. Update the achievement table in `README.md`.
6. Open a PR. CI will validate the meta.yaml schema.
