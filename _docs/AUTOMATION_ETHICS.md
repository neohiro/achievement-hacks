# Automation Ethics

When is automating an achievement legitimate research, and when is it just
griefing with a script? This document is the line, and it is deliberately
specific so that "it's just a badge" cannot be used to argue past it.

This file has been referenced from `README.md` since the repo was created. It did
not exist until 2026-10-03. That gap mattered: for the entire life of this repo
the ethics were implied by tone rather than stated as rules.

## The distinction that does the work

An achievement badge is a **public claim about a person**. When it appears on a
profile, every human who sees it — a potential contributor, a recruiter, a
maintainer deciding whether to trust your code — reads it as evidence of real
activity.

That makes badge automation fall into two very different categories:

**Category A — the automation does the work, and the badge reports it.**
A script that opens a PR, and the badge appears because a maintainer reviewed
and merged it. The badge is *accurate*. Scripting the tedium around real work is
just tooling.

**Category B — the automation produces the badge without the work.**
A script that opens and immediately closes an issue, or mass-reacts ❤️ to
strangers' comments, or opens 50 empty commits with a `Co-authored-by:` trailer.
The badge is *false*. The script's only effect is to make a public claim untrue.

We document Category A. We do not build Category B, and we do not run it.

## The rules

1. **Do not automate anything that touches a third party's account without
   their consent.** Opening issues, commenting, reacting, or opening PRs on repos
   you do not own imposes a cost on a stranger: their inbox, their moderation
   queue, their review burden. Mass-producing such actions is spam, and it is
   harassment when it is repeated.

2. **Do not automate badge issuance on the neohiro account.** Our own profile is
   the evidence base for this entire repo. If we farm badges on it, every status
   in `_achievements/*/meta.yaml` becomes unfalsifiable.

3. **Do not write scripts whose only output is a badge.** If a script's
   purpose is to make an achievement appear rather than to accomplish a task,
   it is Category B. This is why there is no `grant_all.py`, and why adding one
   will be rejected. It is not a missing feature; it is a refusal.

4. **Read-only tooling is always fine.** Reading a public profile, reading star
   counts, rendering the catalog — these change nothing and cost nobody. This is
   the entire `_scripts/` surface we maintain: `grant_check.py`,
   `list_achievements.py`, and the issue-filing helper.

5. **Disclosure is not permission to exploit.** `SECURITY.md` describes how each
   badge can be farmed. That is legitimate: it is the argument for GitHub fixing
   the mechanics. It stops being legitimate at the moment we use the technique
   on anyone, including ourselves.

## How the catalog classifies itself

Applying the rules above to the recipes this repo documents:

| Achievement | Documented recipe | Category | Position |
|---|---|---|---|
| `starstruck` | Ship something people star | A | Fine. No automation can shortcut it. |
| `pull-shark` | Keep merging PRs | A | Fine. Already earned organically (Silver). |
| `open-sourcerer` | Contribute to a repo you don't own | A, if genuine | **Conditional.** One real contribution is normal open-source participation. Machine-generated PRs aimed at strangers' repos are Category B. |
| `galaxy-brain` | Answer a question, get it accepted | **Not automatable at all** | GitHub requires the acceptance to come from a *different account*, so no script can close the loop. Verified 2026-10-03: two self-answered, self-accepted Q&A threads met every documented condition and earned nothing. The only residual abuse is two-account coordination, which is ordinary spam and not something this repo will help with. |
| `pair-extraordinaire` | A collaborator co-authors a commit | A, if genuine | **Conditional.** Needs a real human who really co-authored. Empty commits with forged trailers are VULN-004. |
| `yolo` | Merge a PR with no review | A | Fine as a finding. Already earned organically. |
| `quickdraw` | Open + close within 5 min | B | Earned once, 2026-08-31, deliberately and documented as such. We are not repeating it, and there is no script to repeat it with. |
| `heart-on-your-sleeve` | React ❤️ to comments | B if automated | Genuine reactions are fine and need no automation. The documented mass-reaction PoC (VULN-003) is described, not shipped. |
| `public-sponsor` | Spend $1 | n/a | Requires money, not code. |

Six of nine are fine or fine-with-conditions. The three that are not fine are
noted as not fine, in the achievement's own README.

`galaxy-brain` deserves a specific note, because it is the case that most
obviously *looks* like Category B and is not. Ask a question, answer it, accept
your own answer — that reads exactly like badge farming, and it is how this repo
previously documented the achievement. It is also simply impossible: GitHub
requires the acceptance to come from a different account. Verified on
2026-10-03, when two threads built that way met every other documented condition
and earned nothing. Our own VULN-006 finding was wrong and has been retracted in
[`SECURITY.md`](../SECURITY.md). The rule earns its keep by catching the
*appearance* of abuse, not just the substance.

## What we will and will not accept as a PR

**Will accept:** a new achievement folder following `ACHIEVEMENT_FORMAT.md`; a
correction to a threshold or a status; a read-only verification script with
tests; a better mitigation proposal in `SECURITY.md`.

**Will reject, with explanation:** any script that earns a badge without the
underlying activity; a script that automates writes against third-party
repositories; a PR that softens the findings in `SECURITY.md` without new
evidence; anything that adds `grant_all.py` by another name.

## The uncomfortable part

`quickdraw` is `Earned` in this catalog. It was earned by opening an issue and
closing it in under a second, which is Category B by the definition above. We
kept it recorded rather than quietly resetting it to `Not yet`, because a catalog
that hides its own failures is worthless.

The honest framing is that a single Quickdraw is a rounding error and a
harmless one — it happened on our own repo, it notified nobody, and it is
precisely the kind of thing the badge was designed to detect, which is why we
wrote it up as VULN-001. What would not be acceptable is the same act repeated
across other people's repositories. The difference is not the technique; it is
who pays for it.

## Reporting

Findings are documented in `SECURITY.md` and filed as issues on this repo via
`_scripts/file_vuln_issues.py`. Each finding proposes concrete mitigations rather
than just demonstrating impact, because a report that only proves a problem is
an exploit demo, not a disclosure.

One standard we hold ourselves to: we do not file a finding whose only evidence
is our own account's badge. See [`VERIFICATION.md`](./VERIFICATION.md) for why
that distinction matters, and for why "I have the badge" is a claim about the
mechanic and never about the rightness of the method.