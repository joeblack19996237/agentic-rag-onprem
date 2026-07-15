Status: ready-for-agent

# Issue 03: Admin Document Management

> Source: `specs/10-build-plan.md` TASK-033 (Phase 2, partial — `GET`/`PUT /v1/admin/documents`, explicitly named in TASK-033's own TDD Red bullet). Traces to `specs/02-requirements.md` REQ-010. `specs/06-api-contracts.md` §3 Admin API (API-A-01, API-A-02). `specs/13-decision-log.md` DEC-107. Verification Pattern: TDD.

## Parent

None — traces directly to `specs/10-build-plan.md` TASK-033. No PRD (see Issue 01).

## What to build

`GET /v1/admin/documents` (cursor-paginated list) and `PUT /v1/admin/documents/{document_id}` (soft-delete via `lifecycle_state`, ACL edit, `authority_state` change) against `ingest/models.py`'s real `documents`/`document_versions` schema (built by `data-foundation` TASK-006).

**List.** Cursor-based pagination per `06-api-contracts.md`'s Pagination section — opaque base64 cursor encoding `{last_seen_timestamp, last_seen_id}`, `next_cursor: null` on the last page. Query params `cursor?`, `limit? (default 50, max 200)` — `06-api-contracts.md`'s own API-A-01 row has no `sort` param, so ordering is a fixed server-side decision, not client-configurable. **Resolved during risk review**: `ORDER BY created_at DESC, document_id DESC` (newest first, `document_id` as a stable tie-break for equal timestamps); the cursor's `last_seen_timestamp` is `documents.created_at` specifically, not `updated_at` — both columns exist on the real `Document` model, and `updated_at` was rejected because sorting by it would move a row to a different page every time it's edited, which is a confusing pagination experience for an admin browsing a list.

**Update.** `{acl?, lifecycle_state?, authority_state?}` request body (all optional, partial update) — exact enum values per `06-api-contracts.md`'s API-A-02 row, confirmed by re-reading it during risk review: `lifecycle_state` accepts only `"deleted"` (no other value — there is no `"active"` input for this field), `authority_state` accepts `"authoritative"|"draft"|"deprecated"`. `lifecycle_state: "deleted"` is a soft delete — the row stays in Postgres; only `TASK-013`-onward's query-path grounding logic (not built yet) is responsible for actually excluding it, so this issue's own scope ends at correctly setting the flag, not at proving retrieval-side exclusion (nothing to retrieve from yet — Phase 3). **Resolved during risk review**: because `"deleted"` is the only accepted `lifecycle_state` value, there is no "undelete" path through this endpoint at all — that's a property of the spec's own schema, not a new restriction invented here; reject any other `lifecycle_state` value (or any `authority_state` value outside the 3 listed) with `400`. An empty `{}` body is also `400` (at least one field required) rather than a silent no-op `200`. `lifecycle_state` and `authority_state` are independent fields (deletion vs. content-authority tier) — there is no "conflicting combination" between them to resolve. The update is a single `UPDATE` statement covering every changed field in one call (SQLAlchemy's normal single-flush behavior), not multiple sequential statements. Authorization for this action is whatever Issue 01's admin-scoped auth already grants — this repo has no finer-grained RBAC tier within "admin" in any spec read so far; don't invent one here.

**Testing tiers, made explicit during risk review** — this issue deliberately uses two different, non-interchangeable test infrastructures, neither of which replaces the other or Manual Verification:
- **Tier A (AC1, AC3, AC5)**: a mocked SQLAlchemy `Session` with the real, compiled query/statement asserted (the pattern `tests/config/test_active_model_version.py` already established, post-test-audit). Proves the code builds syntactically and referentially correct SQL for a *single* call — right table, right columns, right `WHERE`/`SET` clauses. Does not prove anything about results across multiple calls, since a bare mock carries no state between calls.
- **Tier B (AC2, AC4)**: a new `FakeDocumentStore` — an in-memory, dict-backed fake following this repo's established `Protocol` + fake pattern (same shape as `ingest/job_store.py`'s `InMemoryJobStore`), shared across a sequence of calls within one test. Proves the pagination/persistence *algorithm* is correct against known data (e.g. that a `PUT` is actually observable on a later `GET`, that pagination doesn't skip/duplicate rows). Does not touch SQLAlchemy at all, so it cannot catch a real query-construction bug the way Tier A does.
- **What neither tier proves**: that the real, compiled SQL (Tier A) actually produces the results the fake algorithm (Tier B) predicts when run against genuine Postgres — e.g. if the fake's row-comparison semantics quietly diverge from Postgres's actual `>`/`>=` boundary behavior, both tiers could pass while a live deployment still mispaginates. That gap is exactly what Manual Verification below exists to close — it is not incidentally redundant with either tier, it is the reason both tiers are declared insufficient on their own rather than trusted as a full substitute for a live-Postgres check. No live Postgres in this sandbox (`docs/agents/dev-environment.md`).

## Acceptance criteria

- [ ] `GET /v1/admin/documents` returns a cursor-paginated list against a mocked `Session` (Tier A) with a real compiled query asserted — including the `ORDER BY created_at DESC, document_id DESC` clause; `next_cursor` is `null` on the last page
      Verification: `pytest tests/admin/test_documents.py -k lists_paginated -v`
- [ ] Cursor pagination correctly excludes/includes rows when new rows are inserted between two simulated page fetches, using the `FakeDocumentStore` (Tier B), deterministically ordered by `(created_at, document_id)` descending — no record skipped or duplicated across the simulated pages
      Verification: `pytest tests/admin/test_documents.py -k pagination_correct_under_interleaved_insert -v`
- [ ] `PUT /v1/admin/documents/{document_id}` with `{lifecycle_state: "deleted"}` issues an `UPDATE` (Tier A), not a `DELETE` — the row is never removed. **Strengthened during risk review**: assert on the compiled statement's actual `WHERE` clause (targets the requested `document_id`) and `SET`/values (`lifecycle_state` is actually `"deleted"`), not merely that `update()` rather than `delete()` was called — a mock could pass a weaker check while updating the wrong row or the wrong value.
      Verification: `pytest tests/admin/test_documents.py -k soft_delete_issues_update_not_delete -v`
- [ ] `PUT /v1/admin/documents/{document_id}` with an `acl` payload updates `allow_principals`/`deny_principals`, observable on a subsequent `GET` — using the `FakeDocumentStore` (Tier B): seed a document, `PUT` an ACL change, `GET` the same document from the same store instance, assert the change is visible. A bare `MagicMock` Session (Tier A's pattern) cannot satisfy this AC — it carries no state between calls.
      Verification: `pytest tests/admin/test_documents.py -k acl_edit_persists -v`
- [ ] `PUT /v1/admin/documents/{document_id}` for an unknown id returns `404 not_found` — Tier A (mocked `Session`), configured so the query resolves to no row (e.g. `scalar_one_or_none()` returns `None`), not an exception
      Verification: `pytest tests/admin/test_documents.py -k unknown_id_returns_404 -v`
- [ ] Both routes accept **either** a valid JWT **or** a valid admin API key (tested independently), and reject an invalid/missing credential with `401` — reusing Issue 01's middleware
      Verification: `pytest tests/admin/test_documents.py -k requires_auth -v` (parametrized over both credential types plus the missing/invalid case)

## Manual verification

- [ ] [manual-verify] Pagination cursor stability holds under genuine concurrent Postgres transactions (real MVCC visibility, real concurrent writers) — the agent-checkable AC above proves the cursor algorithm is correct given a known row set, not real-database concurrent-transaction behavior.
      Owner: Backend/DevOps. Evidence to capture: a load-test script (N concurrent writers inserting documents + one reader paginating through the full set) run against a real Postgres instance, with a log confirming zero skipped/duplicated rows across the full sweep. **Clarified during risk review**: if a script is written for this, it lives under `tests/load/`, explicitly excluded from `tools/verify.sh`/CI (matching this repo's existing convention that every manual-verify item is a human/DevOps action, not an automated CI gate) — run manually or on a separate schedule, never a PR-merge blocker.

## Blocked by

- Issue 01 (Auth Foundation) — this route needs its auth middleware
