# Verification

How this repo proves that a `status:` claim is true, and how to re-check it.

## Why this document exists

Every achievement in this catalog carries a `status` field, and until 2026-10-03
every single one of them was maintained by hand. That went wrong in both
directions:

| Slug | Claimed | Actually | How it went stale |
|---|---|---|---|
| `pull-shark` | `Not yet` — "total is likely below the Default threshold of 2" | **Silver** | The note itself said "30+ merged PRs", which is above 2. Nobody re-read it. |
| `starstruck` | `Not yet` — "the badge isn't appearing yet. Verification pending" | **Default** | The 16-star threshold was cleared long before; the badge was live the whole time. |
| `yolo` | `Not yet` — "branch protection blocks solo merges" | **Default** | Asserted a repo-level setting that was never checked, and it was wrong. |
| `quickdraw` | README said `Earned`, `meta.yaml` said `Not yet` | **Default** | Two sources of truth, no reconciliation. |

Every one of these was a guess presented as a fact. The fix is mechanical
verification, not more care.

## The one request that settles it

GitHub exposes **no public API** for achievements. There is no
`/achievements` endpoint, no GraphQL type, and no documented way to ask "does
account X hold badge Y". The community reverse-engineered the answer, and
[`grant_check.py`](../_scripts/grant_check.py) uses it:

```bash
python _scripts/grant_check.py neohiro
```

It performs one unauthenticated `GET https://github.com/<login>`, reads the
achievement sidebar, and parses the badge image asset. GitHub encodes the tier
in the asset filename:

| Asset filename | Meaning |
|---|---|
| `pull-shark-silver-0643f87ac9fd.png` | Pull Shark, **Silver** |
| `starstruck-default-b6610abad518.png` | Starstruck, **Default** |
| `yolo-default-be0bbff04951.png` | YOLO, **Default** |
| `quickdraw-default-39c6aec8ff89.png` | Quickdraw, **Default** |

Achievements that can be held more than once additionally render a count badge
(`<span class="achievement-tier-label--silver …">x3</span>`), which is how
`pull-shark` reports Silver held three times over.

### Why scrape HTML instead of guess

The alternative — inferring status from activity signals — is what produced the
table above. Merged PR counts can be private; star counts lag; branch protection
is per-repo and per-branch. Reading the badge GitHub actually renders has exactly
one failure mode: the badge is not there. That failure mode is safe.

## Recording a verification

When `grant_check.py` reports a badge that `meta.yaml` does not know about, fix
`meta.yaml` and record the evidence:

```yaml
earned_on:
  - neohiro
status: Earned
verified:
  account: neohiro
  tier: Silver
  repeat_count: 3
  verified_on: "2026-10-03"
  method: "profile sidebar badge asset 'pull-shark-silver-*' with tier label 'x3'"
  source: "https://github.com/neohiro?tab=achievements"
```

The `verified:` block is not decorative. It records *what was observed* and
*when*, so a future reader can tell a measured fact from a recollection.

## Keeping it honest

Two commands, both read-only, both wired into CI:

```bash
python _scripts/grant_check.py          # meta.yaml vs. the live profile; exit 2 on drift
python _scripts/list_achievements.py --check   # meta.yaml vs. the markdown tables; exit 2 on drift
```

`grant_check.py` exits `2` when a catalog status disagrees with the profile in
either direction — including the `Earned`-but-not-rendered case, which catches
someone disabling the public-profile achievement toggle.

`.github/workflows/catalog-drift.yml` runs both on a schedule and on demand.
Drift is expected to be non-zero right after someone earns a badge; the fix is
always to update `meta.yaml`, never to suppress the check.

## Limits

Be honest about what this does and does not establish.

- **It proves the badge is displayed.** It does not prove *how* it was earned.
  A badge is evidence that the condition was met, not that the condition was
  met honestly.

- **It reads a rendered page, and it guards against that.** GitHub could change
  the markup at any time. Two checks exist specifically so a parser break cannot
  be mistaken for a change in reality:

  | Guard | Detects | Result |
  |---|---|---|
  | `looks_like_profile()` | Logged-out interstitials, JS shells, abuse pages — anything served with HTTP 200 that is not a profile | exit 1 |
  | `count_achievement_cards()` vs. `parse_badges()` | GitHub changing its asset host or badge naming: cards present, badges extracted = 0 | exit 1 |

  Without the second guard, a CDN rename would make every badge silently
  vanish, and the audit would confidently report that four genuinely earned
  achievements were never earned — an error that invites a human to "correct"
  four `meta.yaml` files into `Not yet` and destroy the evidence. Both guards
  print the remediation and refuse to report drift. `--json` carries
  `parser_sanity` and `cards_found` so this is visible without reading prose.

  **If badges ever drop from many to zero, check `cards_found` first.** A
  non-zero card count with zero extracted badges is a broken parser, not a purge.

- **`cards_found` is roughly double `live_badge_count`, and that is correct.**
  GitHub renders the achievement sidebar twice — a desktop block and a
  `d-md-none d-block` mobile block — so each badge appears as two card anchors.
  The live `neohiro` profile reports `cards_found: 8` against 4 unique badges.
  Only the *zero-versus-nonzero* distinction matters for the parser guard;
  do not treat the ratio as meaningful.

- **Deprecated badges never appear.** `arctic-code-vault` and `mars-2020` cannot
  be earned, so absence is expected and is treated as `not-earnable`, not drift.

## CLI contract

Both scripts are designed for CI, so their exit codes are part of the interface:

| Exit | `grant_check.py` | `list_achievements.py` |
|---|---|---|
| 0 | catalog matches the live profile | markdown matches `meta.yaml` |
| 1 | usage, network, catalog, or **parser-break** error | catalog could not be read |
| 2 | **drift** — a `status:` disagrees with reality | markdown is out of sync |

Exit 1 and exit 2 are deliberately distinct. Exit 2 means "the facts changed,
update `meta.yaml`". Exit 1 means "this run proved nothing" and must never be
answered by editing the catalog.

With `--json`, stdout carries only the JSON document and the human summary goes
to stderr, so `grant_check.py --json | jq` works.