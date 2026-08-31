# Achievement Document Schema

Every achievement folder in `_achievements/` must contain at minimum:

```
_achievements/<slug>/
├── README.md        ← human guide (required)
├── meta.yaml        ← machine-readable metadata (required)
├── earn.sh          ← automation script (optional but encouraged)
└── verify.sh        ← verification script (optional but encouraged)
```

## meta.yaml fields

```yaml
slug: starstruck                    # kebab-case, matches folder name
name: Starstruck                    # official display name
emoji: "⭐"                         # primary emoji representation
badge_url: ""                       # github.githubassets.com URL (optional)
tiers:
  - name: Default
    threshold: 16                  # stars on a single repo
  - name: Bronze
    threshold: 128
  - name: Silver
    threshold: 512
  - name: Gold
    threshold: 4096
earned_on: []                      # list of account logins who have earned this
status: Not yet                     # Not yet | In progress | Earned | Deprecated | Unobtainable
earnable: true                      # can new accounts earn this?
deprecated_reason: ""               # set if not earnable
how_earned: ""                      # one-liner
automatable: true                   # is there a deterministic automation?
automation_difficulty: Medium       # Trivial | Easy | Medium | Hard | Impossible
links:
  official_doc: ""                  # docs.github.com URL
  community_repo: ""                # community-maintained reference repo
```

## README.md sections (required)

Every achievement README must contain these sections in order:

1. **Badge** — emoji + name
2. **Status badge** — `Not yet` / `In progress` / `Earned`
3. **One-liner** — what it measures
4. **Visual** — description of the badge appearance
5. **Tiers** — table of tier thresholds
6. **How it works** — detailed explanation
7. **Automated recipe** — the fastest deterministic path (script + walkthrough)
8. **Manual recipe** — the human-friendly version
9. **Difficulty assessment** — why it's this hard
10. **neohiro status** — current progress on this account
11. **Community** — links and references
