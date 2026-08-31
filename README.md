# 🏆 GitHub Achievement Hacks

> Agentic documentation, recipes, and automation for every GitHub Achievement.
> **By the [neohiro](https://github.com/neohiro) org. Made with love, automation, and a few gun emojis.**

---

## What is this?

This repository is the **canonical reverse-engineering of every GitHub Achievement badge** — what they look like, what they do, and **the mathematically friendliest, most user-friendly, network-cheapest, LLM-free way to earn each one** (and, where possible, an automation script that earns it for you).

It is also:

- A **living index** of all GitHub Achievements, including **frozen / deprecated** ones (Arctic Code Vault, Mars 2020) that GitHub no longer issues but still displays.
- A **forward-compatible** design — new achievements slot in without breaking the structure.
- A **public invitation** to GitHub themselves (see "A note to GitHub" at the bottom) to detect, prevent, or rate-limit the automation patterns we document.

We are not here to game a system in bad faith. We are here to:
1. **Document** what the badges are and how they work.
2. **Lower the barrier** for newcomers to earn the badges through real, organic work.
3. **Push the platform** to be more intentional about which automations it rewards.

---

## How to read this repo

```
achievement-hacks/
├── README.md                          ← you are here
├── _docs/
│   ├── ACHIEVEMENT_INDEX.md           ← canonical catalog (single source of truth)
│   ├── ACHIEVEMENT_FORMAT.md          ← schema for adding new achievements
│   ├── STATUS_LEGEND.md               ← meaning of every status flag
│   └── AUTOMATION_ETHICS.md           ← when automation is fair vs. griefing
├── _achievements/
│   ├── <achievement-slug>/
│   │   ├── README.md                  ← what it is, how to earn it, automation recipe
│   │   ├── earn.sh|ps1|py             ← optional one-liner to earn it
│   │   ├── verify.sh|ps1|py           ← check whether you have it
│   │   └── meta.yaml                  ← machine-readable metadata
│   └── _deprecated/                   ← achievements GitHub no longer issues
│   └── _highlights/                   ← account-tier badges
├── _scripts/
│   ├── list_achievements.py           ← cross-platform inventory helper
│   ├── grant_check.py                 ← audit which achievements your account has
│   ├── grant_all.py                   ← the lazy "make them all appear" entry point
│   └── CI/                            ← GitHub Actions workflows
└── .github/
    └── ISSUE_TEMPLATE/
        └── new_achievement.md         ← request a new achievement be added
```

---

## The achievement catalog (current)

| Slug | Name | Tier(s) | Status | Difficulty | Easiest path |
|---|---|---|---|---|---|
| [starstruck](./_achievements/starstruck/README.md) | ⭐ Starstruck | Default → Gold | **Not yet** | Medium | Drive stars to a single repo |
| [pull-shark](./_achievements/pull-shark/README.md) | 🦈 Pull Shark | Default → Gold | **Not yet** | Easy | Keep merging PRs |
| [pair-extraordinaire](./_achievements/pair-extraordinaire/README.md) | 👥 Pair Extraordinaire | Default → Gold | **Not yet** | Trivial | Add `Co-authored-by:` to one merged PR |
| [galaxy-brain](./_achievements/galaxy-brain/README.md) | 🧠 Galaxy Brain | Default → Gold | **Not yet** | Medium | Enable Discussions, answer a question, mark it accepted |
| [quickdraw](./_achievements/quickdraw/README.md) | 🔫 Quickdraw | Default (1) | **Not yet** | Trivial | Open + close an issue within 5 min |
| [yolo](./_achievements/yolo/README.md) | 🏴 YOLO | Default (1) | **Not yet** | Trivial | Merge a PR with zero reviews |
| [heart-on-your-sleeve](./_achievements/heart-on-your-sleeve/README.md) | ❤️ Heart On Your Sleeve | Default → Gold | **Not yet** | Trivial | React with ❤️ to comments |
| [open-sourcerer](./_achievements/open-sourcerer/README.md) | 🌱 Open Sourcerer | Default → Gold | **Not yet** | Medium | Get one commit merged in a public repo you don't own |
| [public-sponsor](./_achievements/public-sponsor/README.md) | 💖 Public Sponsor | Default (1) | **Not yet** | Trivial (but $) | Sponsor a dev for $1 |
| ~~arctic-code-vault~~ | 🧊 Arctic Code Vault | Frozen | **Deprecated** | Unearnable | Contributed to a 2020 GitHub Archive Program repo |
| ~~mars-2020~~ | 🚁 Mars 2020 Contributor | Frozen | **Deprecated** | Unearnable | Contributed to Mars 2020 Helicopter mission code |

### Highlights / account-tier badges

See [`_achievements/_highlights/`](./_achievements/_highlights/) for the **Pro**, **Developer Program Member**, **Security Bug Bounty Hunter**, **GitHub Campus Expert**, and **Security Advisory Credit** badges — all of which require you to enroll in a GitHub-side program, not earn through activity.

---

## Status legend

Every achievement tracks a `status` flag. See [`_docs/STATUS_LEGEND.md`](./_docs/STATUS_LEGEND.md) for the canonical meanings.

| Status | Meaning |
|---|---|
| `Not yet` | We have the recipe and verification, but no one in neohiro has earned it on this account yet. |
| `In progress` | Someone is actively working on it (e.g., waiting for stars, enabling Discussions). |
| `Earned` | Verified earned on the neohiro user account. |
| `Deprecated` | GitHub no longer issues this badge. Recipe is historical only. |
| `Frozen` | (Same as Deprecated — alias used by older community guides.) |
| `Unobtainable` | Requires enrollment in a program outside our control (e.g., Bug Bounty Hunter on GitHub's own platform). |

---

## How to add a **new** achievement (forward-compatibility)

GitHub ships new achievements irregularly. When they do, you add one folder to `_achievements/`, write the README in the documented format, and update [`_docs/ACHIEVEMENT_INDEX.md`](./_docs/ACHIEVEMENT_INDEX.md). The schema and required fields are in [`_docs/ACHIEVEMENT_FORMAT.md`](./_docs/ACHIEVEMENT_FORMAT.md). The folder is named `<slug>` (kebab-case, lowercase).

---

## ⚖️ A note to GitHub

We respect the spirit of achievements. They exist to **celebrate real, sustained contribution** to the platform, and the rare/frozen ones (Arctic Code Vault, Mars 2020) are not earnable today — we don't pretend otherwise.

What we *do* document is that several achievements (Quickdraw, YOLO, Heart On Your Sleeve, the first tier of most others) are **mechanically trivial to acquire by automation**. The scripts in this repository can be used to mass-create + close issues, mass-co-author trivial PRs, and mass-react to comments.

**We invite the GitHub engineering team to:**

1. **Rate-limit** the surfaces that feed these achievements (e.g., require a human time-gap of N minutes for "close within 5 min" badges, weighted by account age).
2. **Tighten the bot detection** on reactions, co-author trailers, and issue close loops so the *cheapest* tiers can only be earned by accounts with real activity.
3. **Surface the badge's intent** — instead of "merged N PRs", display "merged N PRs across N distinct repos over N months" so the badge rewards breadth, not farming.
4. **Publish the actual threshold tables** for achievements like Heart On Your Sleeve and Open Sourcerer so honest users know what they're working toward.

If you'd like to chat about any of this, the maintainers are reachable via Discussions on this repo or by opening an issue.

— The neohiro org

---

## License

MIT. Use these recipes. Improve them. Send PRs. Star the repo (we're working on ⭐ Starstruck Bronze ourselves).
