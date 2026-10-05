# Achievement Document Schema

Every achievement folder in `_achievements/` must contain:

```
_achievements/<slug>/
├── README.md        ← human guide (required)
├── meta.yaml        ← machine-readable metadata (required)
└── earn.sh          ← automation recipe (optional)
```

`verify.sh` was previously listed here. It does not exist and is not expected:
verification is centralized in [`_scripts/grant_check.py`](../_scripts/grant_check.py),
which audits every achievement at once and would make nine per-achievement
verify scripts nine places to rot.

## Evidence status: label every claim

This repo published a false claim once. `galaxy-brain/meta.yaml` asserted that
you can answer your own question and accept your own answer, and shipped a
"deterministic workflow" for earning the badge that way. Following our own recipe
met every documented condition and earned nothing, because GitHub requires the
acceptance to come from a different account. It took a retraction to fix, and
real effort from a maintainer who followed the docs. See
[`SECURITY.md` VULN-006](../SECURITY.md).

The lesson generalises: **a claim's confidence must match its evidence.** Write
`Verified` only for something checked against reality. Everything else is
community-reported folklore that we happen to have copied, and a reader has no
way to tell the difference unless the file says so.

Tier tables must carry an evidence column:

| Tier | Threshold | Evidence |
|---|---|---|
| Default | 2 | community-reported |
| Bronze | 8 | community-reported |

Use exactly these labels, spelled as shown:

| Label | Meaning |
|---|---|
| `Verified` | Checked directly against reality. Add how and when: `Verified - badge held`, `Verified 2026-10-03`. |
| `community-reported` | Widely repeated, no first-party confirmation. |
| `Unpublished` | GitHub does not disclose it and nobody has confirmed it. |

Never write a bare number. "Default: 2" invites a reader to treat it as
documented fact; "Default: 2 | community-reported" invites them to check.

If you discover a claim here to be false, **retract it in place and visibly.**
Do not quietly delete it and do not quietly edit it. A reader who trusted the old
text deserves to learn it was wrong, and the correction is evidence about which
other claims to trust.

## meta.yaml fields

```yaml
slug: starstruck                    # kebab-case, matches folder name (required)
name: Starstruck                    # official display name (required)
emoji: "⭐"                         # primary emoji representation
tiers:
  - name: Default
    threshold: 16                   # stars on a single repo
  - name: Bronze
    threshold: 128
  - name: Silver
    threshold: 512
  - name: Gold
    threshold: 4096
earned_on: []                       # accounts that have earned this
status: Not yet                     # see _docs/STATUS_LEGEND.md (required)
verified: {}                        # evidence block; required when status is Earned
earnable: true                      # can new accounts earn this? (required)
deprecated_reason: ""               # set if not earnable
how_earned: ""                      # one-liner
automatable: true                   # is there a deterministic automation?
automation_difficulty: Medium       # Trivial | Easy | Medium | Hard | Impossible
links:
  official_doc: ""
  community_repo: ""
notes:
  - "free-form caveats"
```

### Required-field rules

`slug`, `status`, and `earnable` are parsed by `_scripts/grant_check.py`, which
runs without PyYAML and therefore matches them as anchored top-level scalars.
Two constraints follow:

- They must be **top-level**, not nested.
- Their values must be exactly the documented strings. `status: earned`
  (lowercase) is treated as malformed, because `STATUS_LEGEND.md` defines
  `Earned` and a silent case-mismatch is how a catalog rots quietly.

An unrecognised `status` or `earnable` is reported as `malformed` and fails the
audit. It is never treated as `Not yet`.

### The `verified:` block

Required whenever `status: Earned`. This is the field that separates a measured
fact from a recollection, and it is the reason the 2026-10-03 stale-status
incident cannot recur silently.

```yaml
status: Earned
verified:
  account: neohiro            # the login that was checked
  tier: Silver                # tier read from the badge asset
  repeat_count: 3             # optional; only when GitHub renders an "xN" label
  verified_on: "2026-10-03"   # ISO date
  method: "profile sidebar badge asset 'pull-shark-silver-*' with tier label 'x3'"
  source: "https://github.com/neohiro?tab=achievements"
```

`method` should name the artefact actually observed, so a future reader can
re-derive the conclusion rather than trust it. `_scripts/list_achievements.py`
exposes the block under `--json` as `verified`, and
`tests/test_scripts.py::TestRealCatalog` fails if any `Earned` entry lacks one.

The block covers the account's own status. It does **not** license unverified
claims about how the achievement works in general — see
[Evidence status](#evidence-status-label-every-claim) above, and
[`VERIFICATION.md`](./VERIFICATION.md) for the mechanism. An `Earned` badge proves
the condition was met; it does not document the rules, and reading one from the
other is how the VULN-006 claim survived as long as it did.

## README.md sections

An earlier version of this document required eleven sections in a fixed order
(`Badge`, `Status badge`, `One-liner`, `Visual`, `Tiers`, `How it works`,
`Automated recipe`, `Manual recipe`, `Difficulty assessment`, `neohiro status`,
`Community`). **No achievement README in this repo ever followed it** — the
`Badge`, `Status badge`, and `One-liner` sections do not exist anywhere, and
section order varies. A contract nobody follows is worse than no contract,
because it reads as enforced. The real convention is below.

### Required, in this order

| # | Section | Notes |
|---|---|---|
| 1 | **What it measures** | One or two sentences. Doubles as the one-liner. |
| 2 | **Visual** | Badge appearance and animation; note skin-tone variants. |
| 3 | **Tiers** | Table of thresholds. Write "unpublished" if GitHub does not say. |
| 4 | **How it works** | The actual award condition, including caveats. |
| 5 | **Automated recipe** | The scripted path, **or** an explicit statement that none exists. Required even when the answer is "there isn't one" — silence is indistinguishable from omission. |
| 6 | **Manual recipe** | The human path. |
| 7 | **neohiro status** | Current verified state. Should name the verification method. |
| 8 | **Difficulty assessment** | Why it is rated as it is. |

Section 1 doubles as both "Badge" and "One-liner" from the old contract: the
`# <emoji> <Name>` H1 carries the badge, and "What it measures" carries the
one-liner.

### Optional

| Section | When |
|---|---|
| **⚠️ Ethics note** | Required in practice for any achievement whose recipe touches a third party's account or whose automation is documented as abusive. See [`AUTOMATION_ETHICS.md`](./AUTOMATION_ETHICS.md). |
| **Community** | External references and badge catalogs. |

### Status line

Every README opens with a status line directly under the H1:

```markdown
> **Status: `Earned`** — Silver (128 merged PRs), verified 2026-10-03 against the live profile.
```

It must agree with `meta.yaml`. `_scripts/list_achievements.py --check` does not
parse this line, so the audit relies on `meta.yaml` as the single source of
truth — but a README that contradicts its own `meta.yaml` is a documentation bug
and should be fixed in the same commit.

## Adding an achievement

1. Create the folder with `meta.yaml` and `README.md`.
2. Add your row to both catalog tables by hand - the `README.md` catalog and
   `_docs/ACHIEVEMENT_INDEX.md`. There is no generator; see the note in
   `README.md` ("The catalog table is maintained by hand") for why.
3. Run `python _scripts/list_achievements.py --check` and `python _scripts/grant_check.py neohiro`.
4. Open a PR.

CI enforces steps 2 and 3 on every change under `_achievements/`.