Status: ready-for-agent

# PRD: Document Ingest Pipeline (Parse, Chunk, Embed, Index)

> Source: `specs/10-build-plan.md` TASK-008 + TASK-009 (Phase 2). Traces to `specs/02-requirements.md` REQ-001, REQ-002, REQ-003, REQ-037, NFR-012 and `specs/13-decision-log.md` DEC-036, DEC-038, DEC-046, DEC-065, DEC-086. Workflow reference: `specs/03-workflows.md` Workflow 1 — Document Ingest.

## Problem Statement

An enterprise admin or a CCM/ECM vendor's automated sync process has a document that needs to become queryable. Today there is no ingest path at all: no way to submit a document, no way to know whether it parsed, no way to know when it is safe to query. Until a document is parsed, chunked, embedded, and indexed with its access-control data attached, it cannot be found by any query, and if it were indexed without its ACL data, it would leak content to users who should not see it.

## Solution

A single HTTP seam, `POST /v1/ingest`, accepts a supported-format document and returns a `document_id` and a `status_url` within one second. Behind that seam, an asynchronous pipeline parses the document, splits it into fixed-size overlapping chunks, embeds each chunk with a dense+sparse embedding model, attaches Layer 1 access-control and retention metadata to each chunk's payload, and writes the result into the vector index. The caller polls `GET /v1/ingest/{document_id}` and sees the job progress through `pending → parsing → indexing → ready` (or `failed`). Only after a chunk reaches the index with its ACL payload attached is it retrievable by any query.

## User Stories

1. As an enterprise admin, I want to upload a PDF/Word/Markdown/plain-text document, so that its content becomes queryable by my organization's users.
2. As an enterprise admin, I want an immediate `document_id` and status URL on upload, so that I don't have to block on a long-running HTTP call to know my upload was accepted.
3. As an enterprise admin, I want to poll ingest status, so that I know when a document is safely queryable versus still processing.
4. As an enterprise admin, I want an upload in an unsupported format to be rejected immediately with a clear list of supported formats, so that I don't wait for a job that can never succeed.
5. As a CCM/ECM vendor integrator, I want to trigger ingest via an automated sync process (not just manual upload), so that documents already living in the host ECM/CCM system stay in sync without a human copy-pasting files.
6. As an enterprise admin, I want every chunk of a document to carry the same access-control list as the source document at the time of ingest, so that a user without permission to see the source document can never see it via a query answer.
7. As an enterprise admin, I want a document's retention state captured at ingest time, so that documents under legal hold or past their retention window are excluded from future answers even if the retrieval-time ECM check lags.
8. As an enterprise admin, I want ingest failures (unreachable embedding service, unreachable ECM ACL lookup) to retry rather than silently drop the document, so that a transient outage doesn't produce a permanently un-ingested document with no visible error.
9. As an enterprise admin, I want an in-progress ingest job to resume from its last completed step after a service restart, so that a `docker compose restart` mid-ingest doesn't force me to re-upload and re-process from scratch.
10. As an end user querying the system, I want documents that finished ingest to be retrievable within their normal query latency budget, so that a newly indexed document behaves like any other document, not a second-class one.
11. As an enterprise admin, I want a large document (up to the reference 100-page benchmark) to reach `ready` status within a bounded time (≤ 60s on reference hardware), so that ingest throughput is predictable and demoable.
12. As a system operator, I want it to be structurally impossible for a chunk to be written to the index without its ACL payload attached, so that a race condition or partial failure cannot produce a universally-visible chunk (fail-closed, not fail-open).

## Implementation Decisions

- **Seam**: `POST /v1/ingest` is the single external seam. It is asynchronous — the response contract is `{document_id, status_url}`, not the final ingest result. `GET /v1/ingest/{document_id}` exposes job status. Re-uploading the same file content produces a new `document_id`; content-level idempotency is the caller's responsibility, not this pipeline's.
- **Format support and rejection**: Supported formats are PDF (text-extractable), Word (`.docx`), Markdown, and plain text. Unsupported formats are rejected synchronously with `415 unsupported_media_type` and the supported-format list, before any job is created.
- **Parsing**: Unstructured.io is the primary parser; PyMuPDF is the rescue path for PDF layouts Unstructured mangles; `python-docx` handles Word. OCR and complex-table extraction are explicitly deferred (out of scope below).
- **Chunking**: Fixed chunk size of 1024 tokens with 128-token overlap. Recursive splitter is the primary strategy; a structural splitter (markdown headers, PDF sections) is the fallback. `chunk_id` is immutable, keyed by `(document_id, version_id, sequence)` — this identity must never be reassigned once a chunk is created, since citation and audit records depend on it staying stable.
- **Embedding**: `bge-m3`, served via TEI, in a single forward pass that produces both a dense vector and a sparse vector (this is why `bge-m3`, not a dense-only model, was chosen — hybrid dense+sparse retrieval has no other source for the sparse side in this stack).
- **ACL enrichment (Layer 1)**: Before a chunk is written to the index, its payload is enriched with `allow_principals[]`, `deny_principals[]`, `security_label`, and `retention_state`, sourced from `ECMAdapter.get_effective_acl()` and `ECMAdapter.get_retention_state()`. This is Layer 1 of the two-layer authorization model; Layer 2 (live re-check at query time) is out of scope for this pipeline and belongs to the retrieval path.
- **Identity must never enter the embedding vector.** ACL and identity fields are payload-only metadata alongside the vector, never part of the text that gets embedded. This is a hard constraint, not a style preference — an embedding that encodes identity could leak access information through vector similarity itself.
- **Index write**: Qdrant collection, keyed by `<corpus_id>_<embedding_model_version>`. A chunk is only considered indexed once its vector and full ACL/retention payload are written together — partial writes (vector without ACL payload, or vice versa) must not be observable as a retrievable state.
- **Job durability and resume**: Ingest jobs are Postgres-backed (`job_queue` table, `SELECT ... FOR UPDATE SKIP LOCKED` dispatch pattern — no separate queue broker). Each pipeline step (parse, chunk, embed, index) persists its intermediate result before advancing job status, so a mid-job restart resumes from the last completed step rather than restarting the whole document.
- **Failure handling**: If the embedding service is unreachable, the job requeues with backoff and remains visible at `status = pending` with an ops-visible retry count — it must not silently hang. If the ECM ACL lookup is unreachable, ingest blocks entirely rather than defaulting to an unrestricted/no-ACL payload; a chunk must never be written to the index without its ACL payload, even under a dependency outage.
- **Status state machine**: `pending → parsing → indexing → ready` on the happy path; any state can transition to `failed` on an unrecoverable error. This is a per-job state (lives in `job_queue`), separate from the whole-document lifecycle state on the `documents` row.
- **Modules touched**: `ingest/` (parse, chunk, embed, ACL enrichment, index-write steps), `config/` (embedding model version pinning), `acl/` is read-only consumed here (not modified) via `ECMAdapter`.

## Testing Decisions

- Tests target the `POST /v1/ingest` → `GET /v1/ingest/{document_id}` seam and observable index state — not the internal parse/chunk/embed functions in isolation. Only external behavior (job status transitions, final index content and payload shape) is asserted.
- TDD Red for the parse+chunk step: uploading a supported-format document returns a `document_id` within 1s and an initial `pending` status; uploading an unsupported format returns 415 with no `document_id` issued.
- TDD Red for the embed+enrich+index step: a chunk's embedding input never contains an ACL/identity field (this is a static/CI-enforceable check, not just a runtime assertion); a chunk's Qdrant payload contains `allow_principals[]`, `deny_principals[]`, `security_label`, `retention_state` correctly populated. Use a `LocalAdapter` (no live ECM) for this test per the no-ECM fast-path.
- Acceptance test: end-to-end ingest of a sample 100-page PDF reaches `ready` status and its chunks are retrievable via a direct Qdrant query, within the reference-hardware timing budget.
- The NFR-012 "no identity in embedding vector" check must be enforceable in CI as a static check, not only as a per-test runtime assertion — a regression here is a security defect, not a functional one.
- Chunk immutability (`chunk_id` stability per `(document_id, version_id, sequence)`) should be asserted directly, since citation/audit correctness in later pipeline stages depends on it.
- Prior art: none yet in this codebase (this is the first pipeline being implemented); `specs/11-test-plan.md`'s `TEST-###` catalog should be consulted for the canonical test IDs this PRD's tests map to before implementation starts.

## Out of Scope

- OCR and complex-table extraction (deferred to a later phase, per DEC-036).
- Layer 2 authorization (live re-check at query time) — this is the retrieval path's concern, not ingest's. This PRD only covers Layer 1 (ACL enrichment at write time).
- CDC-driven re-ingest on document version changes (webhook or poll-based sync from the host ECM) — covered by separate build-plan tasks (CDC consumer tasks), not this PRD.
- The `GET /v1/ingest/{document_id}` response's full status-object schema beyond the state machine itself (exact JSON shape is defined in `specs/06-api-contracts.md` §2 and should be implemented as specified there, not re-derived here).
- Legal-hold freeze and cache invalidation behavior for already-indexed chunks — covered separately (retention/legal-hold build-plan tasks).
- Multi-host / distributed job queue (Postgres `SELECT FOR UPDATE SKIP LOCKED` is explicitly a single-host MVP/V2 pattern; V3 multi-host may reconsider per DEC-038).

## Further Notes

- This PRD merges two build-plan tasks (TASK-008, TASK-009) into one vertical slice because they share a single external seam and neither is independently demoable: a document that only reaches "parsed and chunked" but not "embedded and indexed" is not yet queryable, so splitting them into separate issues would create an issue with no independently verifiable, user-visible outcome.
- `specs/10-build-plan.md` estimates ~4 days (team) / ~8 days (solo) for TASK-008 and ~5 days (team) / ~9 days (solo) for TASK-009 — combined, expect this to be the largest single slice in Phase 2.
- The repo has no `CONTEXT.md` or `docs/adr/` yet, so no existing domain-glossary or ADR conflicts were found to flag. Domain vocabulary used above (`ingest/`, `job_queue`, `Layer 1 ACL enrichment`, chunk state machine) is taken directly from `specs/03-workflows.md` and `specs/13-decision-log.md` to keep this PRD consistent with the canonical spec set once `CONTEXT.md` is eventually seeded.
- If a future PRD revisits any decision cited here (e.g. the embedding model choice in DEC-086, or the chunk size in DEC-065), follow the repo-root `CLAUDE.md` rule: append a supersedes entry to `specs/13-decision-log.md` and check `docs/adr/` for anything needing supersession.
