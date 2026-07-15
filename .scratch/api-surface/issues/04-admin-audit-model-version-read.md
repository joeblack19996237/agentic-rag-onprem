Status: ready-for-agent

# Issue 04: Admin Audit List + Model-Version Read

> Source: `specs/10-build-plan.md` TASK-033 (Phase 2, partial — `GET /v1/admin/audit` and `GET /v1/admin/config/models` only; the NDJSON SIEM pull `GET /v1/admin/audit/events` is explicitly `TASK-035`'s job, blocked on `TASK-024`'s audit-write path, and is out of scope here). Traces to `specs/02-requirements.md` REQ-008, REQ-010. `specs/06-api-contracts.md` §3 Admin API (API-A-03, API-A-06). `specs/13-decision-log.md` DEC-107. Verification Pattern: TDD.

## Parent

None — traces directly to `specs/10-build-plan.md` TASK-033. No PRD (see Issue 01).

## What to build

`GET /v1/admin/audit` (paginated read over `audit/models.py`'s `audit_events` table) and `GET /v1/admin/config/models` (active `model_versions` row per role).

**Audit list.** `audit_events` exists as a real, migrated table (`data-foundation` TASK-006) but nothing in this codebase writes to it yet — no code anywhere constructs an `AuditEvent(...)` row outside the model file itself (confirmed by grep while drafting this issue). `TASK-024` (not built) is what eventually writes real rows during query handling. This issue's own scope is the *read* side only: given rows seeded directly into a mocked `Session`/fake store, `GET /v1/admin/audit` returns them correctly filtered (`from`, `to`, `user_id`) and cursor-paginated. Don't wait on `TASK-024` — a read endpoint over an existing (if currently empty in production) schema doesn't need a producer to already exist to be correctly built and tested, the same way `document-ingest-pipeline`'s tests never needed a live Postgres to prove `job_queue` read/write logic.

**Model-version read.** Extends `config/active_model_version.py`'s existing `get_active_model_version(session, role=...)` (built for the ingest pipeline's own need) into a list-all-roles read: `generation`, `embedding`, `rerank`, `nli`, `safety_input`, `safety_output`, `policy` (the seven roles named in that module's own `NoActiveModelVersionError` docstring). No new query pattern, just a loop over the known role set reusing the existing single-role query.

**Response shape, resolved during the post-publish `/verifiable-acceptance-criteria` re-check**: `06-api-contracts.md`'s own wording ("Active `model_versions` per role") doesn't say whether the response is the full DB row or just the version — and `get_active_model_version` itself only returns the bare `model_version` string, not a row. Return `{role, model_version}` pairs for each of the 7 roles (extending the existing function's return type with the role it was queried for) — not the full `model_versions` row (`adapter_name`, `is_active`, timestamps, etc. are internal bookkeeping this read-only admin surface doesn't need to expose).

**Real-Postgres ceiling.** Same as Issue 03 — pagination correctness is proven algorithmically against a seeded fake, not against genuine concurrent Postgres transactions. See Manual Verification.

## Acceptance criteria

- [ ] `GET /v1/admin/audit` returns audit events filtered by `from`/`to`/`user_id`, cursor-paginated, against seeded fixture rows in a mocked `Session`
      Verification: `pytest tests/admin/test_audit.py -k lists_filtered_paginated -v`
- [ ] Cursor pagination correctly excludes/includes rows when new rows are inserted between two simulated page fetches (same approach as Issue 03's pagination AC)
      Verification: `pytest tests/admin/test_audit.py -k pagination_correct_under_interleaved_insert -v`
- [ ] `GET /v1/admin/config/models` returns a `{role, model_version}` pair for every one of the 7 roles (not the full `model_versions` row — see "Response shape" above)
      Verification: `pytest tests/admin/test_config_models.py -k lists_active_version_per_role -v`
- [ ] Both routes require admin-scoped auth, reusing Issue 01's middleware. **Fixed during the post-publish `/verifiable-acceptance-criteria` re-check**: this AC covers both routes, so both test files need a `requires_auth` case — a single command against one file silently left the other route's auth unverified.
      Verification: `pytest tests/admin/test_audit.py -k requires_auth -v && pytest tests/admin/test_config_models.py -k requires_auth -v`

## Manual verification

- [ ] [manual-verify] Audit-list pagination cursor stability holds under genuine concurrent Postgres transactions — same gap and same evidence bar as Issue 03's manual-verify item, applied to `audit_events` instead of `documents`.
      Owner: Backend/DevOps. Evidence to capture: same load-test approach as Issue 03, against `audit_events`.

## Blocked by

- Issue 01 (Auth Foundation) — these routes need its auth middleware
