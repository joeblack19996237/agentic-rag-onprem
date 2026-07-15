Status: ready-for-agent

# Issue 02: Ingest HTTP Routes

> Source: `specs/10-build-plan.md` TASK-033 (Phase 2, partial — wires `POST /v1/ingest` + `GET /v1/ingest/{document_id}` to the already-built pipeline; admin routes are Issues 03-04). Traces to `specs/02-requirements.md` REQ-001, REQ-008. `specs/06-api-contracts.md` §2 Ingest API (API-I-01, API-I-02). `specs/13-decision-log.md` DEC-107. Verification Pattern: TDD.

## Parent

None — traces directly to `specs/10-build-plan.md` TASK-033. No PRD (see Issue 01).

## What to build

Wire `POST /v1/ingest` and `GET /v1/ingest/{document_id}` to `ingest/pipeline.py`'s already-built, fully-tested pipeline (`document-ingest-pipeline` Issues 01/02) — the first time that pipeline becomes reachable over HTTP rather than only directly callable.

**`POST /v1/ingest`.** Multipart upload (field name `file`; accepted MIME types per `06-api-contracts.md` — `application/pdf`, DOCX, `text/markdown`, `text/plain`). Must return `{document_id, status_url}` promptly — the response must not wait for parsing/chunking/embedding to complete.

**How "promptly" is actually achieved and tested here**: schedule the pipeline call via FastAPI `BackgroundTasks` rather than awaiting it inline in the request handler. **Known limitation, found while drafting this issue**: this repo's `TestClient` (and `httpx.AsyncClient` + `ASGITransport`) cannot observe "the response arrived before the background task finished" — both drive the whole ASGI lifecycle, including scheduled background tasks, to completion before returning control to the caller, so a response-timing assertion against an artificially slow background task will not prove non-blocking in this test harness (confirmed empirically against this repo's FastAPI install; it is not simply untested, the naive approach is unable to observe the property at all here). Test the *structural* property instead: a call-inspection proxy confirming the handler schedules the pipeline call via `background_tasks.add_task(...)` (or equivalent) rather than calling/awaiting it directly in the request path — same style as `ingest/qdrant_setup.py`'s payload-index call-inspection proxy (DEC-141), used there for the same reason (the real property isn't observable directly in this sandbox). The literal ≤1-second wall-clock SLA (REQ-001) is a product-level performance target for `TEST-032`-style baseline tracking (DEC-139) once that harness exists — out of this issue's scope to prove end-to-end.

This uses FastAPI's own in-process `BackgroundTasks`, not `TASK-010`'s Postgres job-queue dispatcher (`SELECT ... FOR UPDATE SKIP LOCKED`) — if the process crashes mid-job, the job is left stuck at its last checkpoint (`ingest/checkpoints.py` already handles the checkpoint half; nothing currently re-polls a stuck job). That gap is `TASK-010`'s explicit job to close, not this issue's — say so plainly in the code these routes add, so a future reader doesn't read "background" as "crash-resilient."

**`GET /v1/ingest/{document_id}`.** Returns `{status, progress, errors}` per `06-api-contracts.md`. `ingest/job_store.py`'s `JobPhase` enum (its actual states — check the enum directly, don't assume names) does not map 1:1 onto the API contract's `status` enum (`pending | parsing | indexing | ready | failed`) — define this mapping explicitly as part of this issue's implementation, in one place, rather than let it drift into ad hoc per-call-site translation.

**Format rejection.** An upload in an unsupported MIME type is rejected `415` before a `document_id` is issued at all — this is a different (earlier, cheaper) rejection point than the pipeline's own internal `UnsupportedFormatError` (which fires after a job would otherwise have been created); the HTTP layer should reject at the multipart-parsing boundary, not by creating a job just to immediately fail it. **Found during the post-publish `/verifiable-acceptance-criteria` re-check**: this is a genuinely separate check from `ingest/parsing.py`'s existing extension-based `SUPPORTED_EXTENSIONS` allowlist (one keys off the multipart `Content-Type` header, the other off the filename extension) — keep the two allowlists in sync (the same 4 formats) rather than letting them drift into two independent sources of truth for "what's supported."

## Acceptance criteria

- [ ] `POST /v1/ingest` schedules the pipeline call as a background task rather than awaiting it inline — verified via call-inspection (spy/mock on the scheduling call), not response timing
      Verification: `pytest tests/api/test_ingest_routes.py -k schedules_background -v`
- [ ] `POST /v1/ingest` with a valid multipart upload returns `{document_id, status_url}` matching `06-api-contracts.md`'s shape
      Verification: `pytest tests/api/test_ingest_routes.py -k returns_document_id_and_status_url -v`
- [ ] An upload with an unsupported MIME type returns `415 unsupported_media_type` with `error.details.supported_formats` listing the accepted types, and no `document_id` is issued
      Verification: `pytest tests/api/test_ingest_routes.py -k rejects_unsupported_mime_type -v`
- [ ] `GET /v1/ingest/{document_id}` reflects each of `pending`/`parsing`/`indexing`/`ready`/`failed` correctly, given a `job_store` row seeded directly at that phase (reusing `ingest/job_store.py`'s existing `InMemoryJobStore` fake) — not by racing a real background task in real time
      Verification: `pytest tests/api/test_ingest_routes.py -k status_mapping -v`
- [ ] `GET /v1/ingest/{document_id}` for an unknown id returns `404 not_found`, not an empty/zero-valued status object
      Verification: `pytest tests/api/test_ingest_routes.py -k unknown_id_returns_404 -v`
- [ ] Both routes require admin-scoped auth, reusing Issue 01's middleware (no new auth code)
      Verification: `pytest tests/api/test_ingest_routes.py -k requires_auth -v`

## Blocked by

- Issue 01 (Auth Foundation) — these routes need its auth middleware to enforce credentials
