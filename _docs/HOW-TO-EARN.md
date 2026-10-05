# How to finish each badge

A per-achievement finishing guide for the five still unearned. It states, for
each, what actually earns it, what blocks it today, and which part is a human
step that no script can do.

Verified against the live `neohiro` profile on 2026-10-03. Re-check with:

```bash
python _scripts/grant_check.py neohiro
```

## Where the account stands

| Achievement | Status | Tier held |
|---|---|---|
| 🦈 Pull Shark | `Earned` | Silver |
| 🔫 Quickdraw | `Earned` | Default |
| ⭐ Starstruck | `Earned` | Default |
| 🏴 YOLO | `Earned` | Default |
| 🧠 Galaxy Brain | `In progress` | — |
| ❤️ Heart On Your Sleeve | `Not yet` | — |
| 🌱 Open Sourcerer | `Not yet` | — |
| 👥 Pair Extraordinaire | `Not yet` | — |
| 💖 Public Sponsor | `Not yet` | — |

Four of nine held. The remaining five split three ways: **one is structurally
impossible**, **three need a person or money**, and **none can be automated by
this repo on purpose** — see [Why there is no earn script](#why-there-is-no-earn-script).

---

## 🌱 Open Sourcerer — most reachable

**Earns:** a commit merged into a public repository you do not own.
**Default tier:** 1 merged PR (community-reported).

This is the only remaining badge obtainable by ordinary work, and it is the one
worth spending effort on: it is real contribution, it compounds into reputation,
and it is the same activity that earns Bronze/Silver/Gold later.

### Steps

1. Find a real target.

   ```bash
   python _scripts/find_contributions.py
   ```

   Read-only. Searches `good first issue`, `help wanted` and `first-timers-only`
   across public repos, excludes ones you can already push to, and caps results
   per repository so a single content farm cannot fill the list.

   ```bash
   python _scripts/find_contributions.py --limit 40 --per-repo 1
   python _scripts/find_contributions.py --label "help wanted" --json
   ```

2. Read `CONTRIBUTING.md` before writing code. This is the step that decides
   whether the PR gets merged. Style guides, commit conventions, test commands.
3. Claim the issue with a one-line comment if nobody has.
4. **Make the change yourself.** One focused change per PR. No drive-by
   reformatting; it buries the diff and costs the maintainer review time.
5. Run the project's tests and note what you ran.
6. **Submit it.**

   ```bash
   python _scripts/submit_contribution.py \
     --repo owner/name \
     --title "Fix typo in README" \
     --closes 42
   ```

   This automates the mechanics around your work, not the work. It refuses to
   run when there is nothing to propose or your changes are uncommitted, because
   a script that opens empty PRs is precisely the spam we decline to send:

   ```
   pre-flight failed: no commits on 'fix-readme' beyond origin/main.
   There is nothing to propose. Make the change first.
   ```

   Use `--dry-run` to see the plan without opening anything.

### Reality check

Expect days, not minutes. A first PR to a popular project may sit unreviewed for
a week or be closed with "see the open roadmap". That is normal and is not a
reflection of quality. Smaller, actively-maintained projects merge far faster —
bias the search with `--label "help wanted"` on projects you actually use.

---

## 👥 Pair Extraordinaire

**Earns:** a commit you co-authored, on a merged PR.
**Default tier:** 1 (community-reported).

### The blocker is a second person

The badge requires a real co-author. The co-author trailer is the mechanism:

```
Co-authored-by: Someone <their-noreply-address>
```

GitHub attributes the commit, and the badge counts it.

### Steps

1. Work with a collaborator on something real — a fix, a review-driven change, a
   refactor you did together.
2. Ensure the commit carries a correct `Co-authored-by:` trailer, or use GitHub's
   "Add co-author" button when creating the commit on GitHub.
3. Get it merged.

### Scripted assistance

```bash
python _scripts/check_coauthor.py           # audit HEAD
python _scripts/check_coauthor.py --last 20 # audit recent commits
python _scripts/check_coauthor.py --branch feature/x
```

Read-only. A malformed trailer still commits, but GitHub attributes it to nobody
**and says nothing** — which is exactly how people conclude the badge is broken
and reach for the forged-trailer "solution". This catches the typo first:

```
  [FAIL] a1b2c3d4e5f6  fix: handle empty trailer
           Co-authored-by: Alex
           -> expected exactly 'Co-authored-by: Name <email@example.com>'
```

Exit `2` means a malformed trailer was found, so CI or a pre-push hook can block
the push.

### Why nothing is automated here

Bulk-generating empty commits with forged trailers is falsifying attribution
metadata inside *other people's* repositories, and it inflates the counter many
times over in a single merge. See
[`AUTOMATION_ETHICS.md`](./AUTOMATION_ETHICS.md) rule 3.

**Fastest honest path:** any collaborator who has ever pushed here. Even a single
one-line fix co-authored with them closes this out.

---

## ❤️ Heart On Your Sleeve

**Earns:** a ❤️ reaction on something you wrote.
**Default tier:** 1 (community-reported); higher tiers **Unpublished**.

### Steps

React ❤️ to comments, issues, PRs and discussions in repositories you actually
use. One reaction on one comment is enough for Default.

### Why nothing is automated here

The documented exploit iterates *scraped comment URLs belonging to strangers* and
fires reactions at each. That is notification spam aimed at people who never
asked for it — the exact behaviour [`SECURITY.md` VULN-003](../SECURITY.md)
describes and this repo declines to ship.

Genuine reactions need no automation. If you are not already reading comments in
public repos, the honest route is to start participating — which is the same work
that makes several other badges here achievable at once.

---

## 💖 Public Sponsor

**Earns:** sponsoring an open-source contributor through GitHub Sponsors.
**Default tier:** 1 (community-reported).

### Steps

1. Pick a project you genuinely depend on.
2. Open its GitHub Sponsors page via the **Sponsor** button on the repo.
3. Choose a one-off amount — $1 satisfies the badge.

### Why there is no script

This one is a **real financial transaction**. There is nothing to automate: the
badge records that money moved from you to a person you chose to support, and a
script cannot and should not move anyone's money. If the expense needs
approving, `Sponsors` may be non-reimbursable depending on your employer's
policy — worth checking before you start.

---

## 🧠 Galaxy Brain — blocked by design

**Earns:** an answer accepted in a Discussion's **Q&A** category, where the
acceptance is made by **a different account**.

### Why it is stuck

This was attempted and failed. Two Q&A threads were created in
`neohiro/achievement-hacks` (#7, #19), each self-answered and self-accepted.
Both are correctly categorised, both carry `isAnswered=true`, and together they
meet the Default threshold of 2. The badge was not awarded.

GitHub requires the accepter and the answer author to be different accounts.
This is an anti-abuse measure: GitHub Community staff described hardening the
rules precisely because people were manufacturing questions with secondary
accounts and accepting their own answers.

Full write-up, including the evidence table and community corroboration:
[`_achievements/galaxy-brain/README.md`](../_achievements/galaxy-brain/README.md)
and [`SECURITY.md` VULN-006](../SECURITY.md).

### Steps

1. Find a public repo with Discussions enabled and an **active Q&A** category
   where people ask real questions. Ours are enabled on 16 repos but have no
   inbound traffic.
2. Answer a question you can genuinely help with.
3. The asker marks it Accepted. Ask politely if they don't; do not pressure them.

### Hard truth about timing

There is no way to put a deadline on this. It depends entirely on a stranger
reading your answer and choosing to accept it. Treat it as opportunistic — do not
plan around it, and do not manufacture a question to prompt yourself.

---

## Why there is no earn script

Five achievements remain and none has a full `earn.sh`. That is deliberate, and
the reasoning is per-achievement rather than a blanket refusal.

### Can it be scripted?

| Achievement | Mechanically scriptable? | Script shipped here | Why |
|---|---|---|---|
| 🌱 Open Sourcerer | **Partly** | `_scripts/find_contributions.py`, `_scripts/submit_contribution.py` | Finding and submitting a contribution *you made* is legitimate tooling. Generating the contribution is spam. |
| 👥 Pair Extraordinaire | **Partly** | `_scripts/check_coauthor.py` | Validating a real co-author trailer is legitimate. Forging 50 empty ones with a second account is not. |
| ❤️ Heart On Your Sleeve | Yes, abusively | none | The only vector is mass-reacting to scraped strangers' comments. That is notification spam. |
| 🧠 Galaxy Brain | **No** | none | The final step is a decision by another human. Not merely discouraged — impossible. |
| 💖 Public Sponsor | No | none | A real financial transaction. |

### The research picture

For completeness, and because it is legitimate to *describe* an exploit even
when shipping it would be wrong, the automation vectors are written up as
security findings in [`SECURITY.md`](../SECURITY.md):

| Finding | Achievement | Vector described |
|---|---|---|
| VULN-001 | Quickdraw | Scripted open-then-close issue loop |
| VULN-002 | YOLO | Admin override to merge unreviewed |
| VULN-003 | ❤️ Heart On Your Sleeve | Scrape comment URLs, react to each |
| VULN-004 | 👥 Pair Extraordinaire | N empty commits + forged `Co-authored-by:` trailers |
| VULN-005 | 🦈 Pull Shark | Automated low-quality PRs |
| VULN-006 | 🧠 Galaxy Brain | **Retracted** — GitHub already requires a different accepter |
| VULN-007 | 🌱 Open Sourcerer | Third-party PR spam as an achievement path |

Documentation of a weakness is how GitHub learns to fix it. Shipping the
exploit is how the weakness spreads. This repo does the first and not the second,
which is also why [`AUTOMATION_ETHICS.md`](./AUTOMATION_ETHICS.md) rule 5 says
disclosure is not permission to exploit.

### The scripts we do ship

All three are assistive. None produces a badge without the underlying activity.

```
_scripts/find_contributions.py    find real targets           (read-only)
_scripts/submit_contribution.py    open a PR for your change   (one write, pre-flight checked)
_scripts/check_coauthor.py        validate co-author trailers (read-only)
```

`submit_contribution.py` is the only one that writes to GitHub, and it refuses to
run when there is nothing to propose or your work is uncommitted — because a
script that opens empty PRs is exactly the spam we are declining to send.

If you want to propose automation for one of the five, read
[`AUTOMATION_ETHICS.md`](./AUTOMATION_ETHICS.md) first, and expect it to be
rejected unless it only ever touches repositories you control.