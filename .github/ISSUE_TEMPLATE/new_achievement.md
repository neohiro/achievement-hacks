---
name: New achievement
about: Propose an achievement that is missing from the catalog
title: "[NEW-ACHIEVEMENT] <name>"
labels: ["new-achievement"]
assignees: ""
---

## Which achievement?

<!-- The GitHub display name, e.g. "Starstruck". If you are adding something
     that has no badge on GitHub at all, say so explicitly. -->

## Badge appearance

<!-- Emoji/graphic, tier colours, and the profile animation if there is one.
     A link to the hovercard detail view on someone's profile is ideal:
     https://github.com/<account>?tab=achievements -->

## Tiers

<!-- The actual thresholds, if you know them. If they are unknown, write
     "unpublished" rather than estimating — an invented threshold in this
     catalog is worse than a blank, because it gets cited. -->

| Tier | Threshold | Source |
|---|---|---|
| Default | | |
| Bronze | | |
| Silver | | |
| Gold | | |

## Earn condition

<!-- What GitHub actually measures. Quote the documentation if it exists. -->

## Is it automatable?

<!-- If yes, describe the mechanism at a high level and note whether it harms
     third parties. Read _docs/AUTOMATION_ETHICS.md first: if the only way to
     earn it is spam on someone else's repository, say that plainly instead of
     shipping a script. -->

- [ ] No automation exists
- [ ] Automatable, but only on infrastructure the account controls
- [ ] Automatable, and it acts on third-party accounts

## Evidence

<!-- How do you know this is earned-able? A public profile showing the badge is
     the strongest form. Link it. Do not use your own unreproducible claim as
     the only evidence. -->

## Checklist

- [ ] `_achievements/<slug>/meta.yaml` added, following `_docs/ACHIEVEMENT_FORMAT.md`
- [ ] `_achievements/<slug>/README.md` added, with all 11 required sections
- [ ] catalog tables updated by hand (`README.md` and `_docs/ACHIEVEMENT_INDEX.md`)
- [ ] `python _scripts/list_achievements.py --check` passes
- [ ] `python _scripts/grant_check.py neohiro` shows no drift
- [ ] I have read `_docs/AUTOMATION_ETHICS.md` and this adds no badge-farming automation