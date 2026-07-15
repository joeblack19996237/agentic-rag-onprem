# Test Audit — 2026-07-15

> Second run, per `.claude/skills/test-audit/SKILL.md`. The first run (`test-audit-2026-07-14.md`) covered only Phase 1's 14-function scaffold suite. Everything under `tests/acl/`, `tests/config/`, `tests/db/`, and `tests/ingest/` — 94 functions across 12 files — is Phase 2 work that has never been audited before. Triggered directly by the user, immediately after `document-ingest-pipeline` Issue 02 landed.

**Date**: 2026-07-15
**Scope**: every test file in `docs/testing.md`'s inventory table (18 files, 108 functions after this round's additions). `tests/architecture/test_import_graph.py` and `tests/api/test_ready.py` confirmed unchanged since the 2026-07-14 audit (`git log` shows no commits touching either file since their original implementation) — not re-read function-by-function, since nothing about them could have changed. Everything else read in full and checked cold against the taxonomy, most of it for the first time.
**Method**: ran `pytest -v` first (per the skill's step 2) to establish real pass/fail state, then read every test function against `tdd/tests.md`'s taxonomy (tautological, implementation-coupled) + `docs/testing.md`'s "What to avoid" (accidentally-correct `sys.path`, weakened deliberately-red test, unproven check-style test) + the two general checks (vacuous, swallowed failure). Confirmed via `find tests -name "*.py" -not -name "__init__.py"` that every file under `tests/` appears in `docs/testing.md`'s inventory — no missing-from-inventory finding.

## Suite state at audit time

```
108 items collected — 107 passed, 1 failed (after this round's 2 fixes)
FAILED tests/api/test_ready.py::test_ready_reports_every_service_healthy
```

The one failure is the same deliberately-red test the 2026-07-14 audit already confirmed — re-checked here: still red for the documented reason (Phase 1 has no backend services wired), assertion unchanged (`body["ready"] is True`), not weakened.

## Findings

Two real gaps found and fixed directly (both met the skill's "correct assertion is unambiguous from context" bar — the actual code under test was read to derive the fix, not guessed). Nothing flagged for human judgment this round.

| File:Line | Anti-pattern | Fixed / Flagged |
|---|---|---|
| `tests/config/test_active_model_version.py::test_selects_model_version_column_of_model_version_table` | **Vacuous relative to its own claim.** The test's name and file both claim to verify `config/active_model_version.py`'s query, but the body only asserted `ModelVersion.__tablename__ == "model_versions"` — a fact about `config/models.py`'s class definition, never calling `get_active_model_version()` at all. The function's own comment admitted this ("just documents the intent"). A wrong-SELECT-column bug would have passed this test silently. | **Fixed.** Read the real implementation (`config/active_model_version.py:28`, `select(ModelVersion.model_version).where(...)`), compiled it live to confirm the exact rendered string, then rewrote the test to call the real function with a mocked session and assert the compiled query starts with `SELECT model_versions.model_version` — the same mock+compile pattern the adjacent `test_query_filters_on_role_and_is_active` already used for the WHERE clause. Verified via mutation testing: swapping the real query's column to `ModelVersion.adapter_name` makes the fixed assertion fail as expected. |
| `tests/docs/test_doc_drift.py` — missing case for `find_issue_status_mismatches` | **Missing test / incomplete coverage of a documented convention.** `docs/testing.md`'s own "cover both directions" rule wasn't fully applied to the 2026-07-14 cross-feature-collision fix: `test_distinguishes_same_numbered_issues_across_different_features` only covers the no-false-positive direction (two colliding-numbered issues that each independently agree). Nothing tested whether a *real* mismatch inside one of two colliding-numbered issues still gets caught and correctly attributed, rather than masked by the other feature's clean state — which is exactly the shape the original bug had. | **Fixed.** Added `test_detects_a_real_mismatch_inside_a_cross_feature_number_collision`: two features both named "Issue 01," one with a genuine README/Status mismatch, one clean. Asserts exactly one violation, correctly naming the stale feature and not the clean one. Verified via mutation testing against a reconstructed pre-fix (bare-number-keyed) version of the checker: it returns `[]` on this exact scenario — the real mismatch is silently swallowed, confirming this is a genuine gap the new test closes, not a redundant addition. |

**Everything else checked clean** — no tautological, implementation-coupled, vacuous, or swallowed-failure pattern found; no accidentally-correct `sys.path` risk (bare `pytest`, no `python -m` prefix, resolved every import cleanly); every mocked SQLAlchemy `Session`/external-library call is a legitimate boundary mock (an injected constructor dependency or an external I/O client), not an internal collaborator reached into privately:

- `tests/acl/test_ingest_stub.py` (6 functions) — real round-trips through `FakeACLLookup`, real fail-closed checks, `SqlAlchemyACLLookup` tests mock only the `Session` boundary and assert real field mapping + real call shape. One of these (`test_sqlalchemy_acl_lookup_raises_when_no_row_found`) was already confirmed load-bearing via mutation testing during implementation, not just this audit.
- `tests/db/test_migration.py` (8 functions) — runs the real Alembic CLI via `subprocess` against the real migration file and asserts on real rendered DDL; as close to a live check as this sandbox allows. `test_upgrade_array_typed_fields_are_not_jsonb` is a real regression guard for a bug a prior code-review pass actually caught.
- `tests/ingest/test_checkpoints.py` (4), `test_chunking.py` (9), `test_job_store.py` (8), `test_qdrant_setup.py` (6), `test_tokenizer.py` (4) — all real round-trips, real windowing-algorithm output checked against independent hand-written literals (not recomputed), real `QdrantClient(":memory:")` queries, real network-backed tokenizer calls. `test_in_memory_job_store_advance_does_not_drop_earlier_keys`'s own comment documents it was *already* strengthened once before, for the same "recomputed the wrong way" shape this audit looks for — confirmed the current version is genuinely correct, not just re-flagged.
- `tests/ingest/test_embedding.py` (11), `test_parsing.py` (9), `test_retry.py` (4), `test_pipeline.py` (28) — Issue 01/02's own suite, all real `httpx.MockTransport`/`QdrantClient(":memory:")`/in-memory-built PDF-DOCX fixtures. Mocks of `dense_client`/`sparse_client` in `HybridTEIEmbeddingClient` tests and `embedding_client` fault-injection in the pipeline's retry tests are both injected constructor dependencies (the public composition seam), not private internals. `test_acl_lookup_failure_blocks_ingest_and_writes_no_chunk` was mutation-tested during implementation, twice — the first mutation attempt was itself flawed (only neutered one of two ACL calls) and had to be redone.

## Summary

| Item | Result |
|---|---|
| Test functions audited this round | 94 new (never previously audited) + 2 re-confirmed unchanged (`test_ready.py`, `test_import_graph.py`, not re-read) = 108 total in the current suite |
| False-confidence patterns found | 2 |
| Fixed | 2 (both verified via mutation testing after the fix, not just re-run) |
| Flagged for human judgment | 0 |
| Inventory completeness | Clean — no test file outside `docs/testing.md`'s table |

Both gaps this round share a shape worth naming: a test's *name* claimed more than its *body* actually checked (a column-selection claim that never called the function under test; a collision-safety claim that only tested one of two required directions). Neither was caught by `code-review` at the time each test was written, nor by the discipline that wrote genuinely careful mutation tests for the *other*, higher-stakes tests in the same session (ACL fail-closed, the doc-drift collision fix itself) — mutation-testing the load-bearing tests doesn't substitute for cold-rereading the rest of the suite, which is exactly the zoom-level shift this skill exists for. Both fixes were verified load-bearing the same way: mutate the real code back toward the bug the test claims to prevent, confirm the fixed test actually fails.
