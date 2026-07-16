# Commit History Sweep

> Second sweep, per `CLAUDE.md`'s "Commit history sweeps" section. Not a per-diff review (that's `code-review`/`peer-review`'s job) — this looks across the whole commit history for patterns only visible at that zoom level.

**Date**: 2026-07-16
**Scope**: `c45f90c..969ac95` (22 commits) — picks up from `commit-sweep-2026-07-13.md`'s cutoff. Spans the rest of Phase 2's `data-foundation`/`document-ingest-pipeline` work and the full `api-surface` (TASK-033) four-issue arc.
**Method**: `git log --oneline`/`--shortstat`/`--name-only` for size and touch-frequency, read every issue-implementation commit body, cross-checked against `.scratch/session-feedback.md`'s per-issue entries and the two rules `commit-sweep-2026-07-13.md`'s own follow-on (`c1fe82d`) promoted into `CLAUDE.md`, to see whether they actually held up in the four commits that came after them.

## Findings

### F.1 — Both rules promoted after the last sweep were followed in every commit since, with a visible shift in what `/code-review` actually finds

`c1fe82d` (the commit immediately after the last sweep) promoted two rules from Issue 01/02 friction: (a) capability claims need empirical verification, not just version/import checks; (b) self-check the diff against the issue's own prose *before* invoking `/code-review`, since code-review is a second gate, not a substitute for a first one.

Checked whether these actually held across Issues 01-04 rather than assuming: (a) Issue 01 verified `PyJWT[crypto]`'s real dependency graph before pinning it; Issue 04 verified `datetime.fromisoformat`'s `Z`-suffix support empirically before relying on it for `from`/`to` parsing — both are real instances of the promoted rule being applied, not just cited. (b) More tellingly, `/code-review`'s *finding shape* changed measurably: Issues 01 and 02 (before the rule existed) each had `/code-review` catch something a careful self-read plausibly could have caught first — a vacuous test, a sync/async wording mismatch, an issue-text/implementation mismatch on "requeue" semantics. Issues 03 and 04 (after the rule, with the self-check step actually performed first each time) had `/code-review` catch *zero* such issue-text-vs-code mismatches — every finding in both was a pure code-quality smell (duplicated pagination-boundary logic, an overloaded exception, a docstring citing the wrong issue number) that a self-check pass wouldn't be expected to catch anyway, since it's not about the issue text at all. That's the rule doing its job, not the rule being untested — worth recording as confirmed-working rather than leaving it as an unverified assumption the next feature might silently stop applying.

### F.2 — Mutation-testing has now been applied at least once in every feature this Phase, and has never once come back clean-with-nothing-to-report

`document-ingest-pipeline` Issue 01 (ACL-lookup fail-closed), `api-surface` Issue 01 (the JWKS-only-holds-asymmetric-keys finding), Issue 02 (JWT `kid` gap), Issue 03 (3 mutations: ORDER BY, soft-delete `SET` value, interleaved-insert boundary — all caught real gaps, one of which showed a return-value-only assertion would have missed a persisted-wrong-value bug), Issue 04 (3 more, same track record). Every single application of this technique across 5 separate issues in 2 different features has surfaced a real, non-obvious finding — zero instances of "ran it, it was already fine." This isn't a gap to fix, it's evidence the technique is worth its cost every time it's used and should stay a standing default for any test whose whole claim is "this specific bug can't happen," not just something applied occasionally.

### F.3 — New environmental discovery this sweep should surface, not bury in one issue's session-feedback entry

Issue 04 hit a real, previously-unknown constraint of this execution environment: the sandbox's own safety classifier blocks running code with `Depends(require_auth)` deliberately removed (the standard mutation-testing pattern this session used successfully three times prior — Issue 03's two routes, Issue 04's audit route — then blocked on Issue 04's fourth attempt, `/v1/admin/config/models`). This is exactly the shape of fact `docs/agents/dev-environment.md` exists to hold ("probed capabilities... for the current execution environment") but it currently only covers Docker/GPU/compiler-toolchain/CI-access — not this. Recommend a follow-up: add a row or note there so a future session doesn't have to rediscover "auth-disabling mutation tests aren't reliably available here" from scratch, and doesn't misread a classifier denial as a tool bug. Not fixed in this sweep (a docs-only change outside this sweep's own scope of *finding* patterns, not authoring new doc content) — flagged for the next session or the user to action.

### F.4 — The `tests/<domain>/conftest.py` mypy-collision fix was scoped correctly, not under-documented

Confirmed by checking: it's only actually recurred once so far (`tests/admin/conftest.py`'s creation in Issue 03; Issue 04 extended that same file rather than creating a third colliding one), and per this project's own explicit discipline ("only promote a repeated observation into a standing rule once it's actually recurred, not on first mention"), it correctly stayed at the `docs/testing.md`/`pyproject.toml`-comment level rather than being promoted into `CLAUDE.md` alongside the two `c1fe82d` rules. No action needed — noting this because a sweep should also confirm when a scoping judgment call was right, not only flag when one looks wrong.

## Not flagged

Commit sizes and message quality stay consistent with the last sweep's baseline — no oversized commits, no message/diff mismatches found this pass. File-touch frequency (`docs/testing.md` 12×, `session-feedback.md` 11×, `README.md` 9× across 22 commits) confirms the "closing out a work cycle" checklist's doc-update steps are being followed on essentially every commit, not just when convenient.
