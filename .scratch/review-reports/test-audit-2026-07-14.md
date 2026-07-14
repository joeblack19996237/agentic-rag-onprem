# Test Audit

> First-ever run, per `.claude/skills/test-audit/SKILL.md`. Not a diff review (that's `code-review`/`peer-review`'s job) and not authoring-time discipline (that's `tdd`'s job) — this rereads the *existing, accumulated* test suite cold for false-confidence patterns.

**Date**: 2026-07-14
**Scope**: every test file in `docs/testing.md`'s inventory table — `tests/architecture/test_import_graph.py`, `tests/api/test_ready.py`, `tests/docs/test_doc_drift.py` (14 test functions total). Confirmed via `Glob tests/**/*.py` that nothing under `tests/` falls outside this set — the inventory table is complete, no missing-from-inventory finding.
**Method**: ran `pytest -v` first (per the skill's step 2) to establish real pass/fail state, then read every test function against the taxonomy in `tdd/tests.md` + `docs/testing.md`'s "What to avoid" section, plus the two general checks (vacuous, swallowed failure).

## Suite state at audit time

```
14 items collected — 13 passed, 1 failed
FAILED tests/api/test_ready.py::test_ready_reports_every_service_healthy
```

The one failure is `test_ready_reports_every_service_healthy`, which is documented in its own docstring and in `docs/testing.md`'s "What to avoid" section as **deliberately red** — Phase 1 has no backend services wired, so `ServiceHealth()` defaults every field to `False` (`api/main.py:20-29`) and `ready` computes to `False`. Confirmed this is red for the documented reason (an honest not-ready state), not a weakened assertion masking as something else — the assertion still reads `body["ready"] is True`, unchanged from what the docstring describes.

## Findings

None. Every one of the 14 test functions was checked against the full taxonomy and came back clean:

| File | Function | Tautological? | Implementation-coupled? | Vacuous? | Swallowed failure? |
|---|---|---|---|---|---|
| `test_import_graph.py` | `test_no_violations_in_current_scaffold` | No — independent literal (`[]`) | No — public function only | No | No |
| `test_import_graph.py` | `test_detects_a_forbidden_import` | No — independent literal (`1`, specific substrings) | No — real synthetic scenario via `tmp_path`, public interface | No | No |
| `test_import_graph.py` | `test_forbidden_imports_only_names_known_modules` | No — cross-checks two independently-declared constants for consistency, not a recomputation | No — both `FORBIDDEN_IMPORTS`/`MODULES` are exported, not private | No | No |
| `test_ready.py` | `test_ready_returns_dec117_schema_shape` | No — independent shape/type checks | No — real `TestClient` HTTP call | No | No |
| `test_ready.py` | `test_ready_reports_every_service_healthy` | No — independent literal (`True`) | No | No | No — deliberately red, see above, not a false-confidence case |
| `test_doc_drift.py` | 3x `test_current_repo_has_no_*` | No — independent literal (`[]`), gates CI against the real repo | No — public function only | No | No |
| `test_doc_drift.py` | `test_detects_a_dangling_dec_reference` | No — independent literal + substring | No — synthetic `tmp_path` fixture, public interface | No | No |
| `test_doc_drift.py` | `test_ignores_dec_ids_that_do_resolve` | No — independent literal (`[]`) | No | No | No |
| `test_doc_drift.py` | `test_detects_duplicate_dec_ids` | No — independent literal + substring | No | No | No |
| `test_doc_drift.py` | `test_detects_a_closed_issue_still_shown_pending_in_readme` | No — independent literal + substring | No | No | No |
| `test_doc_drift.py` | `test_detects_a_premature_done_claim_in_readme` | No — independent literal + substring | No | No | No |
| `test_doc_drift.py` | `test_no_mismatch_when_readme_and_status_agree` | No — independent literal (`[]`) | No | No | No |

No `sys.path`/accidentally-correct-invocation risk either — bare `pytest` (no `python -m` prefix) resolved every first-party import cleanly in the run above, consistent with `pyproject.toml`'s `pythonpath = ["."]`.

## Summary

| Item | Result |
|---|---|
| Test functions audited | 14 / 14 |
| False-confidence patterns found | 0 |
| Fixed | 0 (none needed) |
| Flagged for human judgment | 0 |
| Inventory completeness | Clean — no test files outside `docs/testing.md`'s table |

This repo's existing test suite is small (3 modules, 14 functions) and was built under explicit TDD + anti-pattern discipline from the start (`tdd/tests.md`'s taxonomy, `docs/testing.md`'s "what to avoid" section), which is almost certainly why this first audit came back clean rather than the audit process being weak — the same relationship `commit-sweep-2026-07-13.md` noted between its own clean sections and the project's existing self-correction discipline. A clean result is still a real result, not a skipped check — recorded here so the next audit has a real baseline to diff against as the suite grows past what one person can hold in their head.

No action applied — nothing needed fixing or flagging this round.
