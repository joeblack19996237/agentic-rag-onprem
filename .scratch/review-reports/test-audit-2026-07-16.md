# Test Audit — 2026-07-16

> Third run, per `.claude/skills/test-audit/SKILL.md`. The prior run (`test-audit-2026-07-15.md`) covered 108 functions across 18 files, right after `document-ingest-pipeline` Issue 02 landed and before any `api-surface` work started. Everything added since — `api-surface` (TASK-033) Issues 01-04's HTTP layer — has never been audited. Triggered by `docs/testing.md`'s inventory growth (108 → 189 functions since the last audit) immediately after `api-surface` Issue 04 (the feature's last issue) landed.

**Date**: 2026-07-16
**Scope**: 7 files never previously audited — `tests/api/test_auth.py`, `tests/api/test_openapi_contract.py`, `tests/api/test_query_stub.py`, `tests/api/test_ingest_routes.py`, `tests/admin/test_documents.py`, `tests/admin/test_audit.py`, `tests/admin/test_config_models.py` (81 functions). `tests/architecture/test_import_graph.py`, `tests/api/test_ready.py`, and everything the 2026-07-15 audit already covered confirmed unchanged since (`git log` shows no commits touching any of them between the two audits) — not re-read.
**Method**: ran `pytest -v` first (skill's step 2) to establish real pass/fail state, then read all 7 files cold against the taxonomy (`tdd/tests.md`'s tautological/implementation-coupled, `docs/testing.md`'s accidentally-correct-`sys.path`/weakened-red/unproven-check-style, plus vacuous/swallowed-failure). Cross-referenced every mocked-`Session` test's `side_effect` list length against the real number of `session.execute()` calls the code path under test actually makes, and confirmed every test file appears in `docs/testing.md`'s inventory table (it does — updated in the same commits that added each file).

## Suite state at audit time

```
189 items collected — 188 passed, 1 failed
FAILED tests/api/test_ready.py::test_ready_reports_every_service_healthy
```

Same deliberately-red test the last two audits already confirmed — re-checked here: still red for the documented reason (Phase 1 has no backend services wired), assertion unchanged (`body["ready"] is True`), not weakened.

## Findings

Two real issues found, both fixed directly (met the skill's "correct fix is unambiguous from context" bar). Nothing flagged for human judgment this round.

| File:line | Anti-pattern | Fixed/Flagged |
|---|---|---|
| `tests/api/test_ingest_routes.py:192` (pre-fix) | Overly broad `pytest.raises(Exception)` — the only occurrence of this pattern anywhere in the suite (every other exception-raising test in this codebase asserts a specific type). Would pass even if `ACLOverride.model_validate` raised the wrong kind of error for the wrong reason (e.g. a `TypeError`/`AttributeError` from an unrelated bug), not just "correctly rejected as invalid". Doesn't cleanly match the repo's named taxonomy categories, but is the same underlying risk implementation-coupled/swallowed-failure tests share — a test that can't distinguish "passed for the right reason" from "passed for any reason". | **Fixed**: confirmed empirically (`ACLOverride.model_validate(...)` on a Pydantic model actually raises `pydantic.ValidationError`) before narrowing, not guessed. Re-ran after the fix — still passes for the right reason. |
| `tests/api/test_query_stub.py:33-41` (pre-fix) | Not a taxonomy match (assertions are correct, nothing swallowed, nothing vacuous) — a general test-hygiene gap worth fixing anyway: `test_query_stub_unauthenticated_request_is_401_not_404` mutates shared `app.state.jwks`/`app.state.admin_api_key` directly (the only way to exercise "no credentials configured", since `require_auth` reads `request.app.state` itself rather than a `Depends()`-injected value) and never restored them. No observed failure today — every *other* test in the suite happens to go through the `client` fixture, which resets both values on every invocation — but that makes this test's correctness depend on an unrelated fixture's side effect rather than being self-contained, which is fragile if a future test module runs between this one and the next `client`-fixture use without going through it. | **Fixed**: wrapped in `try`/`finally`, saving and restoring the previous values. Re-ran — still passes. |

## Not flagged

All 7 files' Tier-A `mocker.MagicMock()` tests correctly size their `side_effect` lists against the real call count each code path makes (including the easy-to-miss extra `_fetch_current_acl`/existence-check calls inside `admin/document_store.py` and `audit/event_store.py`) — no under- or over-mocked `side_effect` list found. All cursor-pagination and mutation-testable assertions in `tests/admin/` were already mutation-tested during their own issue's implementation (documented in each test's docstring or the issue file's Done annotations) rather than only at this audit — re-verified two of them cold (`test_lists_paginated_with_correct_order_by_and_null_cursor_on_last_page`'s `ORDER BY` assertion, `test_soft_delete_issues_update_not_delete`'s `.compile().params` check) by re-reading rather than re-running the mutation, and both still target the real, load-bearing behavior they claim to. `test_cursor_encode_decode_round_trips` (`tests/admin/test_audit.py`) is a round-trip test (`decode(encode(x)) == x`) — not tautological under this repo's specific definition (it doesn't recompute the expected value the way the code computes it; encode and decode are different functions in different directions), a standard and accepted limitation of round-trip tests generally, not a finding.
