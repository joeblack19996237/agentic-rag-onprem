# Session Feedback

> Running log of *how the work went* — friction points, ambiguous instructions, mistakes caught late, things that worked well enough to repeat. Not a changelog: commit messages and `specs/13-decision-log.md` already cover *what* changed; this file is for the meta-layer neither of those capture. See `CLAUDE.md`'s "Session feedback" section for when to append and when to read.
>
> **Last read: 2026-07-13** (this file's own creation — nothing to catch up on yet).

## 2026-07-13 — CLAUDE.md/spec-tooling improvement pass (P0–P7)

**Context**: a long session implementing 8 concrete improvements against 2026 agentic-coding best practices (CLAUDE.md-as-router drift fixes, DEC-135 verification tiering, a doc-drift CI check, `docs/testing.md`, a pre-commit baseline, closing gaps in another session's cross-model `specs/` review, a handoff-doc convention + git tag, and moving/wiring up `docs/coding-standards.md`), plus this file.

**What worked well enough to repeat**:
- The loop of investigate → cite concrete evidence (exact file:line, not a general impression) → propose 2-4 scoped options → let the user pick one at a time → execute → verify by actually running it → report, repeated across every P-item. Keeping scope to one chosen item per turn kept each change reviewable and avoided speculative work nobody asked for.
- Actually running things caught real bugs that reading alone would have missed: `ruff-format` silently reformatting two unrelated files the first time it ran, the local `mypy` pre-commit hook needing an explicit `args: ["."]` (bare `pass_filenames: false` doesn't invoke it the way CI does), and the doc-drift checker's own regression proof — reproducing the exact hand-fixed README bug in a temp copy before trusting the tool, not just trusting its synthetic test fixtures.
- Not trusting a "this is already done" claim at face value: when told a cross-model review of `specs/` had already been triaged and fixed by a session with no visible history here, spot-checking the claimed fixes against real file content (not just reading the report) and running the mechanical safety nets surfaced two genuine incomplete-propagation gaps (a Drift Log row that stopped 3 findings into a 30-finding round, a missing Re-audit Note). The verification cost was small; skipping it would have left real gaps silently open.

**Friction / mistakes worth naming** (not promoted to standing rules yet — if any of these recur, that's the signal to):
- Appending `DEC-135` to `specs/13-decision-log.md` via an old_string/new_string edit anchored on the *start* of the existing last row (`DEC-134`) inserted the new row *before* it instead of after — broke append/chronological order. Caught only by a follow-up grep, not by the edit itself. When appending to an order-sensitive append-only log, anchor on the end of the current last entry, not the start of the row you don't want to precede.
- Nearly missed `.scratch/document-ingest-pipeline/PRD.md` when checking whether any in-flight `.scratch/` work cited DEC-135's changed content — the mental check defaulted to `.scratch/*/issues/*.md` (matching the issue-tracker doc's own convention) and didn't naturally extend one level up to a feature's PRD. Caught on a later pass, not the first one. "In-flight `.scratch/` work" means the whole feature directory, not just its `issues/` subfolder.
- Introducing a new tool for the first time on an established codebase (here: `ruff-format` via pre-commit) has a real chance of touching files outside the current task's scope, purely as a side effect of "nobody ran this formatter before." Worth specifically diffing what a first-time tool run touches, not just checking whether it passed.
