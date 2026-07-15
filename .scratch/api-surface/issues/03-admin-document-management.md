Status: ready-for-agent

# Issue 03: Admin Document Management

> Source: `specs/10-build-plan.md` TASK-033 (Phase 2, partial — `GET`/`PUT /v1/admin/documents`, explicitly named in TASK-033's own TDD Red bullet). Traces to `specs/02-requirements.md` REQ-010. `specs/06-api-contracts.md` §3 Admin API (API-A-01, API-A-02). `specs/13-decision-log.md` DEC-107. Verification Pattern: TDD.

## Parent

None — traces directly to `specs/10-build-plan.md` TASK-033. No PRD (see Issue 01).

## What to build

`GET /v1/admin/documents` (cursor-paginated list) and `PUT /v1/admin/documents/{document_id}` (soft-delete via `lifecycle_state`, ACL edit, `authority_state` change) against `ingest/models.py`'s real `documents`/`document_versions` schema (built by `data-foundation` TASK-006).

**List.** Cursor-based pagination per `06-api-contracts.md`'s Pagination section — opaque base64 cursor encoding `{last_seen_timestamp, last_seen_id}`, `next_cursor: null` on the last page. Query params `cursor?`, `limit? (default 50, max 200)`.

**Update.** `{acl?, lifecycle_state?, authority_state?}` request body (all optional, partial update). `lifecycle_state: "deleted"` is a soft delete — the row stays in Postgres; only `TASK-013`-onward's query-path grounding logic (not built yet) is responsible for actually excluding it, so this issue's own scope ends at correctly setting the flag, not at proving retrieval-side exclusion (nothing to retrieve from yet — Phase 3).

**Real-Postgres ceiling.** All of this issue's reads/writes are tested against a mocked SQLAlchemy `Session` with a real, compiled query asserted (the pattern `tests/config/test_active_model_version.py` already established, post-test-audit) — no live Postgres in this sandbox (`docs/agents/dev-environment.md`). The pagination-correctness AC below tests the *cursor algorithm* (does it correctly exclude/include rows given a known before/after row set) via a seeded in-memory fake, deterministically ordered by `(timestamp, id)` — it does not and cannot exercise genuine Postgres MVCC concurrent-transaction visibility; that gap is named explicitly in Manual Verification below, not silently assumed proven.

## Acceptance criteria

- [ ] `GET /v1/admin/documents` returns a cursor-paginated list against a mocked `Session` with a real compiled query asserted; `next_cursor` is `null` on the last page
      Verification: `pytest tests/admin/test_documents.py -k lists_paginated -v`
- [ ] Cursor pagination correctly excludes/includes rows when new rows are inserted between two simulated page fetches (seeded fake store, deterministic `(timestamp, id)` ordering) — no record skipped or duplicated across the simulated pages
      Verification: `pytest tests/admin/test_documents.py -k pagination_correct_under_interleaved_insert -v`
- [ ] `PUT /v1/admin/documents/{document_id}` with `{lifecycle_state: "deleted"}` issues an `UPDATE`, not a `DELETE` — the row is never removed
      Verification: `pytest tests/admin/test_documents.py -k soft_delete_issues_update_not_delete -v`
- [ ] `PUT /v1/admin/documents/{document_id}` with an `acl` payload updates `allow_principals`/`deny_principals`, observable on a subsequent `GET`. **Found during the post-publish `/verifiable-acceptance-criteria` re-check**: a bare `MagicMock` Session (the pattern AC1/AC3/AC5 use) carries no state between the `PUT` call and the later `GET` call within the same test, so it cannot actually prove "observable on a subsequent GET" — this AC needs AC2's stateful seeded-fake-store approach instead, not a fresh mock per call.
      Verification: `pytest tests/admin/test_documents.py -k acl_edit_persists -v`
- [ ] `PUT /v1/admin/documents/{document_id}` for an unknown id returns `404 not_found`
      Verification: `pytest tests/admin/test_documents.py -k unknown_id_returns_404 -v`
- [ ] Both routes require admin-scoped auth, reusing Issue 01's middleware
      Verification: `pytest tests/admin/test_documents.py -k requires_auth -v`

## Manual verification

- [ ] [manual-verify] Pagination cursor stability holds under genuine concurrent Postgres transactions (real MVCC visibility, real concurrent writers) — the agent-checkable AC above proves the cursor algorithm is correct given a known row set, not real-database concurrent-transaction behavior.
      Owner: Backend/DevOps. Evidence to capture: a load-test script (N concurrent writers inserting documents + one reader paginating through the full set) run against a real Postgres instance, with a log confirming zero skipped/duplicated rows across the full sweep.

## Blocked by

- Issue 01 (Auth Foundation) — this route needs its auth middleware
