# Achievement Index

Canonical, machine-readable list of all GitHub Achievements known to this repo.

## Schema

Each entry maps to `_achievements/<slug>/meta.yaml`. The index is generated from those files by `_scripts/list_achievements.py`.

## Achievement list

| # | Slug | Name | Tier count | Earnable? | Status |
|---|---|---|---|---|---|
| 1 | `starstruck` | Starstruck | 4 (Default → Gold) | Yes | Not yet |
| 2 | `pull-shark` | Pull Shark | 4 (Default → Gold) | Yes | Not yet |
| 3 | `pair-extraordinaire` | Pair Extraordinaire | 4 (Default → Gold) | Yes | Not yet |
| 4 | `galaxy-brain` | Galaxy Brain | 4 (Default → Gold) | Yes | Not yet |
| 5 | `quickdraw` | Quickdraw | 1 | Yes | Not yet |
| 6 | `yolo` | YOLO | 1 | Yes | Not yet |
| 7 | `heart-on-your-sleeve` | Heart On Your Sleeve | 4 (Default → Gold) | Yes | Not yet |
| 8 | `open-sourcerer` | Open Sourcerer | 4 (Default → Gold) | Yes | Not yet |
| 9 | `public-sponsor` | Public Sponsor | 1 | Yes | Not yet |
| 10 | `arctic-code-vault` | Arctic Code Vault Contributor | 1 | **No** (frozen) | Deprecated |
| 11 | `mars-2020` | Mars 2020 Contributor | 1 | **No** (frozen) | Deprecated |

## Highlights (account-tier, not activity-based)

| Slug | Name | Enrolled? | Status |
|---|---|---|---|
| `github-pro` | GitHub Pro | No | Unobtainable |
| `developer-program-member` | Developer Program Member | No | Unobtainable |
| `security-bug-bounty-hunter` | Security Bug Bounty Hunter | No | Unobtainable |
| `github-campus-expert` | GitHub Campus Expert | No | Unobtainable |
| `security-advisory-credit` | Security Advisory Credit | No | Unobtainable |

## How to add a new achievement

1. Create `_achievements/<slug>/meta.yaml` matching `ACHIEVEMENT_FORMAT.md`.
2. Create `_achievements/<slug>/README.md` following the template.
3. Create `_achievements/<slug>/earn.sh` and/or `_achievements/<slug>/verify.sh`.
4. Add a row to this index.
5. Add a row to `README.md`.
6. Open a PR.

The index in `README.md` is the human-facing version of this file. They should be kept in sync.
