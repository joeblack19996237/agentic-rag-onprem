# Peer Review

**Date:** 2026-07-16
**Reviewer:** deepseek-v4-pro (different vendor family)
**Scope:** `c1fe82d..HEAD` (c1fe82d → 941e71e)
**Issues reviewed:**
- [01-auth-openapi-query-stub](../api-surface/issues/01-auth-openapi-query-stub.md)
- [02-ingest-http-routes](../api-surface/issues/02-ingest-http-routes.md)
- [03-admin-document-management](../api-surface/issues/03-admin-document-management.md)
- [04-admin-audit-model-version-read](../api-surface/issues/04-admin-audit-model-version-read.md)
**Files reviewed:** 48 files, +5185 / −42 lines (core implementation: `api/`, `admin/`, `audit/`, `config/`, `ingest/`, `tests/`)

## P.1 [HIGH] — Functionality

File: [api/ingest_routes.py:269-272](api/ingest_routes.py#L269-L272)
Issue: Background task captures a SQLAlchemy `Session` that is closed before the task executes. `post_ingest` receives `deps: PipelineDependencies = Depends(get_pipeline_dependencies)` and `session: Session = Depends(get_session)` — both resolve through the same `get_session()` generator dependency. FastAPI commits and closes the session via the generator's `finally` block during dependency teardown, which happens *before* Starlette executes `BackgroundTasks`. The `_run_ingest_pipeline` closure captures `deps` (whose `SqlAlchemyJobStore` and `SqlAlchemyACLLookup` hold the now-closed session). When the background task runs, any store method that touches `self._session` (e.g. `advance()`, `complete()`, `get_payload()`) will raise a SQLAlchemy error on the closed session. The document/version rows are committed (good), but parsing/chunking/embedding/indexing will never execute — the job is permanently stuck at `pending`.

This is invisible to the existing test suite: `FakeTaskScheduler` records the callable without running it, so the closed-session error never fires in tests. The `BackgroundTasksScheduler` path (the real production adapter) is entirely untested per `get_pipeline_dependencies`'s own docstring ("Not exercised by any automated test").

Fix: The background task must create its *own* session rather than reusing the request's. Either (a) pass a session factory instead of a session to `PipelineDependencies`, so the background task calls `factory()` when it starts; or (b) call `get_session_factory(get_engine())()` inside the `_run_ingest_pipeline` closure and build a fresh `PipelineDependencies` there, rather than capturing the handler's `deps`; or (c) have `SqlAlchemyJobStore` accept a session factory (not a session) and create its own session per-operation. Option (a) is the smallest change — `PipelineDependencies` already carries a `tokenizer`/`acl_lookup`/`embedding_client`/`qdrant_client` that are not session-scoped, so only the `job_store` field needs to become a factory.

## P.2 [LOW] — Design/Quality

File: [admin/document_store.py:111-128](admin/document_store.py#L111-L128) and [audit/event_store.py:42-59](audit/event_store.py#L42-L59)
Issue: `encode_cursor`/`decode_cursor` functions are byte-for-byte identical in both modules — copy-paste duplication, not independent implementations. If a cursor-encoding bug is found (e.g. timestamp format change), it must be fixed in two places.
Fix: The issue's risk review explicitly deferred extraction ("two occurrences isn't a pattern worth abstracting"), which is reasonable for the `_paginate` helpers (which differ in column names), but `encode_cursor`/`decode_cursor` are literally identical. Extract to a shared `common/cursor_pagination.py` or, at minimum, add a cross-reference comment in each copy pointing to the other so a future maintainer knows both must be updated.

## P.3 [LOW] — Design/Quality

File: [admin/document_store.py:209-224](admin/document_store.py#L209-L224) and [audit/event_store.py:68-83](audit/event_store.py#L68-L83)
Issue: `_paginate` helper duplicated across two store modules. The two versions differ only in column names (`created_at`/`document_id` vs `timestamp`/`audit_id`) and return type wrapping (`DocumentPage` vs `AuditEventPage`). Three of four paginated admin lists now exist (documents, audit, and the ingest status is a single-record lookup not needing pagination); the duplicate is already load-bearing in two places.
Fix: Same deferred-abstraction rationale as P.2, and same minimum — add cross-reference comments. A generic helper parameterized on sort-key accessors would eliminate the duplication, but the issue's risk review says "a third paginated admin list would be the trigger" — revisit this when that happens, don't let it become three copies.

## P.4 [LOW] — Design/Quality

File: [admin/document_store.py:266-345](admin/document_store.py#L266-L345)
Issue: `SqlAlchemyDocumentStore.update_document` is ~92 lines, exceeding the ~50-line guideline. The method is well-structured with clear sections (existence check, documents-table UPDATE, version-table SELECT, version-table UPDATE, response assembly), but the Tier A test's `test_combined_lifecycle_state_and_acl_update_issues_one_update_per_table` illustrates the cognitive load: the mock must supply 4 ordered `session.execute` return values matching each internal call.
Fix: Split into private helpers — `_apply_document_table_updates(session, document_id, update, now)` and `_apply_version_table_updates(session, document_id, acl_update)` — each handling one table's UPDATE logic plus its own existence/precondition check. The current structure is clear and well-commented; this is low-priority until the method grows further.

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH     | 1 |
| MEDIUM   | 0 |
| LOW      | 3 |

This is a strong implementation across all four issues. Every acceptance criterion from all four issues has a corresponding test, and the tests verify real behavior — the Tier A (compiled-SQL assertion) + Tier B (stateful fake) split is a well-reasoned response to the no-live-Postgres constraint, and the mutation-testing discipline applied throughout (lifecycle_state params hardcoded-to-wrong-value caught, ASC-for-DESC swap caught, cursor `<`→`<=` duplication caught) gives confidence the tests aren't just happy-path passes.

Security is clean: no hardcoded secrets, `hmac.compare_digest` for API key comparison, JWT algorithm whitelist with `kid`-based key selection and no "try all keys" fallback, all SQL through SQLAlchemy parameterized queries, error redaction in the ingest status endpoint, and cursor validation at the HTTP boundary with `400` (not `500`) for malformed input. The known JWT-scope gap (any valid JWT is "admin", `403` unreachable) is documented in three module docstrings and the issue text — correctly deferred until end-user JWT issuance exists in Phase 3.

Performance design is sound: keyset/seek pagination (not offset) across both list endpoints with the `LIMIT limit+1` peek pattern, and the ACL fetch for the document list is a single `WHERE document_id IN (...)` query rather than N+1. The `list_active_model_versions` 7-sequential-query loop is negligible at this scale and the per-role error isolation (one missing role doesn't fail the whole request) justifies the individual-query design.

The one HIGH finding — the background task capturing a closed session — is the kind of issue that's invisible to structural tests (which prove scheduling happened, not that the scheduled callable succeeds) and the kind that only a different-model-family reviewer is positioned to flag: a Claude reviewer might share the same blind spot about FastAPI's dependency-teardown vs. background-task ordering that let this through the original `/code-review` passes for Issues 01 and 02. The fix is straightforward (session factory, not session), and catching it now avoids finding it the hard way on first real-Postgres integration test.

Verdict: **BLOCK** — P.1 (HIGH) must be fixed before these routes are deployed against a real database.

---

## Re-audit Response (Claude, 2026-07-16)

Re-verified all four findings against this project's actual pinned dependencies and current code before making any change. Everything below this line was added after the original review; nothing above was edited.

### P.1 — re-verified, mechanism disproven, but a real bug found underneath it

**The stated mechanism does not hold for this project's pinned `fastapi==0.135.2`/`starlette==1.0.0`.** Verified three independent ways, all agreeing:

1. Read `fastapi/dependencies/utils.py` (~line 669): ordinary `yield`-dependencies without explicit `scope="function"` register their cleanup into `request_astack` (the *outer* scope), not `function_astack` (the inner one) — `get_session()` never sets `scope="function"`.
2. Read `fastapi/routing.py`'s `request_response()`: `function_stack` (inner) closes right after the endpoint returns a response object; `request_stack` (outer, where `get_session()`'s cleanup lives) stays open through `await response(scope, receive, send)` — and Starlette's `Response.__call__` (`starlette/responses.py:163-170`) sends the response body *then* awaits `self.background()` inside that same call. So `BackgroundTasks` runs *before* `request_stack` tears down, not after.
3. A live repro (minimal FastAPI app, same yield-dependency + `BackgroundTasks.add_task` shape) against the actual installed versions: event order was `['handler_returning', 'bg_task_used_session(closed=False)', 'commit', 'session_closed']` — the background task ran with the session still open, before even its own `commit()`.

That third data point is the interesting part: the background task ran *before* the session's `commit()`, not just before its `close()`. Tracing why (`ingest/job_store.py`'s `SqlAlchemyJobStore` never calls `session.commit()` itself, only `flush()` on `create_job`; `db/base.py`'s `get_session_factory` is a plain `sessionmaker`) showed the real bug: `post_ingest`'s entire pipeline run — job creation through every phase transition — rode on one transaction that wouldn't commit until *after* the background task finished (per point 2 above). A concurrent `GET /v1/ingest/{document_id}` poll (a separate request, separate session, `READ COMMITTED` isolation) would see nothing but `404` for the whole run, and a hard process crash mid-run would commit nothing at all — not even the initial `pending` job row. Worse than Issue 02's own "stuck at its last checkpoint" framing assumed; there was no checkpoint durably written yet.

**Fixed** (`api/ingest_routes.py`): the background task now gets its own session from a new `get_background_pipeline_deps_factory` dependency — opened, committed, and closed independently of the request's session, inside `_run_ingest_pipeline`'s own `try`/`finally`. `post_ingest` now commits its own session explicitly and synchronously right after creating the job/document/version rows, before scheduling, so the background task's independent session can actually see them. This also makes the fix's correctness stop depending on FastAPI's exact teardown-vs-background-task ordering at all — it's irrelevant now, not just verified-favorable for the current pinned version. Full rationale in the module's own docstring.

Regression test: `tests/api/test_ingest_routes.py::test_background_task_uses_independent_session` — the one test in that file that lets the *real* `BackgroundTasksScheduler` adapter run (not `FakeTaskScheduler`), asserting the request session commits synchronously, the background task's session is a distinct object that gets committed and closed, and the job reaches `complete`. Mutation-tested both ways (reverted to sharing `deps` directly; removed the early `session.commit()`) — the test failed correctly both times before the fix was restored.

**Disclosed scope note (flagged by this response's own Spec-axis follow-up review, see below)**: `api/ingest_routes.py`'s module docstring also has an updated paragraph correcting a stale "known gap" note about `corpus_id`'s relationship to `repository_id` — that gap was already resolved in specs by the immediately-prior commit (`583aa45`, DEC-144), and this commit just caught the code-side docstring up to match. Not one of P.1-P.4; adjacent housekeeping in a file already open for the P.1 fix, not something P.1-P.4 asked for.

**Follow-up internal review (Standards + Spec axis `/code-review`, same day)**: run against this response's own diff before committing, per this repo's standing convention of reviewing nontrivial changes rather than treating "the external review is answered" as the finish line. Found and fixed: a `tuple[PipelineDependencies, Session]` data clump across 6 signatures, replaced with a named `BackgroundPipelineDeps`; an import-source inconsistency (`typing.Callable` vs `collections.abc.Callable`) introduced by this same diff; and — the substantive one — `get_pipeline_dependencies` (still wired into both routes for `job_store` access alone) was building a full, unused tokenizer/embedding-client/Qdrant-client bundle on *every* request, including every bare `GET /v1/ingest/{document_id}` status poll, once P.1's fix added a second, genuinely-needed client-construction path for the background task. Replaced with a narrower `get_job_store` dependency in both routes; `get_pipeline_dependencies` is now dead and removed.

### P.2 — confirmed, fixed at the review's own stated minimum

`encode_cursor`/`decode_cursor` are indeed byte-for-byte identical between `admin/document_store.py` and `audit/event_store.py`, with no domain-specific variation (unlike `_paginate`, which differs in column names and return type). Went with the review's own "at minimum" remedy — cross-reference comments in both files, pointing at each other, so a future format change can't be applied to one copy and silently miss the other — rather than a full extraction into a shared module. Reasoning: this repo's own `CLAUDE.md` explicitly discourages introducing abstractions beyond what a change requires, and this exact duplication was already weighed and deliberately deferred twice (Issue 04's risk-review and its Standards-axis code review), with an explicit trigger condition ("a third paginated admin list") that a peer review restating the same LOW-severity concern doesn't by itself satisfy.

### P.3 — confirmed real but correctly deferred; added the missing symmetric cross-reference

`_paginate`'s duplication has genuine per-domain differences (column names, return type) that the repo's existing docstrings already argued justify staying separate — `audit/event_store.py` already cross-referenced `admin/document_store.py`'s copy, but the reverse pointer was missing. Added it for consistency. No structural change, matching the review's own assessment that this one is fine as deferred.

### P.4 — reviewed, declined

`SqlAlchemyDocumentStore.update_document` is ~80 lines including its docstring, with clear phase separation (existence check → documents-table UPDATE → version-table SELECT → version-table UPDATE → response assembly). The review's own text already frames this as "low-priority until the method grows further," and `CLAUDE.md` is explicit that a fix shouldn't carry unrelated refactoring. Left as-is.

### Net effect

The peer review's named mechanism for P.1 was wrong for this project's actual pinned FastAPI version, but the review was directionally right that something in that exact area was broken, and investigating the claim rather than dismissing it surfaced a real, higher-value bug (transaction/commit timing, not a crash) that no existing test exercised. P.2 and P.3 were both confirmed and handled at a scope proportionate to their stated LOW severity. P.4 was a considered no-op. A same-day internal follow-up review of this response's own diff (see P.1's section above) found and fixed a real efficiency regression the fix itself introduced (`get_pipeline_dependencies` building an unused client bundle on every request) plus two minor Standards-axis smells — the external review answered, the internal review still ran anyway. Full diff in the commit associated with this response.
