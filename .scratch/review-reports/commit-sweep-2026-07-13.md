# Commit History Sweep

> First-ever sweep, per `CLAUDE.md`'s "Commit history sweeps" section. Not a per-diff review (that's `code-review`/`peer-review`'s job) — this looks across the whole commit history for patterns only visible at that zoom level.

**Date**: 2026-07-13
**Scope**: full history, `111eadb..c45f90c` (25 commits) — first sweep, so no prior range to pick up from
**Method**: `git log --name-only` for file-touch frequency, `git log --shortstat` for commit-size distribution, grepped commit messages for recurring "fix/stale/gap/correct" language, spot-checked the flagged commits' own bodies/diffs

## Findings

### F.1 — The same structural risk has surfaced twice, and only the specific instance got fixed each time

`2c9e35e`'s message ("fix observability gap (DEC-128); reconcile with concurrent DEC-127") records two sessions independently minting the same `DEC-127` id because neither could see the other's uncommitted work — `specs/confirmed-context.md`'s own Drift Log row for that round names the lesson explicitly: "`update-specs`'s Step 1/Step 2 ... must be re-run immediately before commit ... whenever work spans multiple concurrent sessions." That's a real fix, but scoped to *ID collisions*.

This session (`72334f7`) hit the same underlying risk in a different shape: a prior session had already triaged and fixed the 2026-07-13 cross-model review's 30 findings, but its `confirmed-context.md` Drift Log entry stopped after 3 of them, and `specs/14-spec-audit-report.md` got no Re-audit Note at all — not because anyone did the work wrong, but because a second concurrent-visibility session boundary meant the propagation steps weren't fully closed out before the next session picked up the thread. Same root cause (work spanning session boundaries loses shared state), different surface (incomplete propagation, not an ID clash).

Two data points isn't a trend, but it's the same failure shape twice, and each fix addressed only the specific manifestation, not the underlying condition. Worth watching for a third occurrence rather than treating either fix as having closed the risk generally.

### F.2 — Roughly a third of commits are corrective, not forward progress

8 of 25 commits (`72334f7`, `5b321ea`, `bddd6d8`, `faa48e2`, `0c4f2d7`, `3f10252`, `2c9e35e`, `9fcfa21`) have "fix"/"stale"/"gap"/"correct" in their own subject line. This is consistent with the project's own visible practice of catching and logging its own mistakes rather than hiding them (every one of these has a full decision-log entry explaining what was wrong and why) — not, on its own, evidence of sloppiness. Named here as a baseline to compare future sweeps against: if the ratio trends up over time as the codebase grows, that's a different signal than if it stays flat or falls.

### F.3 — `72334f7`'s size (25 files, 818 insertions) is a deliberate batch, not organic scope creep

Flagging this so a future sweep doesn't misread it: this commit bundles several independently-scoped pieces of work (CLAUDE.md/README drift fixes, the doc-drift CI check, a pre-commit baseline, and closing two propagation gaps in another session's cross-model review) into one commit because the user explicitly asked for "一次性commit" (commit everything at once) after reviewing each piece separately across several conversation turns. The scope was reviewed incrementally before the commit, just not committed incrementally. Contrast with unreviewed scope creep, which this isn't.

## Nothing else flagged

No recurring bug-fix shape beyond F.1, no file thrash pattern beyond what's expected of `specs/13-decision-log.md`/`confirmed-context.md`/`00-index.md` (append-only files that legitimately receive an edit on every decision round, not a smell), and no commit message that misdescribes its own diff on spot-check. Said plainly rather than padding the findings list, per this repo's own peer-review convention.

## Summary

| Finding | Severity |
|---|---|
| F.1 — concurrent-session propagation risk, two manifestations | Worth tracking |
| F.2 — ~1/3 of commits are corrective | Observation, baseline only |
| F.3 — large commit is user-directed batching | Not a finding, context for future sweeps |

No action applied — this sweep's job is surfacing cross-commit patterns, not fixing them. F.1 is the one worth carrying forward: if a third instance of the concurrent-session-visibility problem shows up in a future sweep, that's the point to design an actual mitigation (e.g., a pre-commit check that greps for uncommitted `DEC-###`/propagation-step markers left by a *different* session) rather than fixing the third instance by hand too.
