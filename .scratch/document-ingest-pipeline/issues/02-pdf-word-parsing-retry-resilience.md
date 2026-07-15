Status: ready-for-agent

# Issue 02: PDF/Word Parsing + Embedding-Service Retry Resilience

> Source: `specs/10-build-plan.md` TASK-008 + TASK-009 (Phase 2, remaining scope — PDF/Word formats + retry resilience). Traces to `specs/02-requirements.md` REQ-001, REQ-002, NFR-001 and `specs/13-decision-log.md` DEC-036, DEC-038. Verification Pattern: TDD.

## Parent

None — traces directly to `specs/10-build-plan.md` TASK-008 + TASK-009, via `.scratch/document-ingest-pipeline/PRD.md`. No parent issue.

## What to build

Widen Issue 01's ingest pipeline to accept PDF (text-extractable) and Word (`.docx`) documents, and add retry-with-backoff specifically for embedding-service outages. Issue 01's ACL-lookup-failure fail-closed behavior already covers the ECM-outage case; this issue does not touch that path.

**Dependency pinning (found during `/verifiable-acceptance-criteria`, 2026-07-14 — resolved during risk review, 2026-07-15)**: `unstructured==0.18.32`, `pymupdf==1.28.0`, `python-docx==1.2.0` are now pinned in `requirements.txt`. `unstructured==0.18.32` is deliberately **not** PyPI's overall latest (`0.24.1`) — every release from `0.20.0` onward requires Python `<3.14`, incompatible with this repo's Python 3.14 pin (DEC-134); `0.18.32` is the newest release that still supports 3.14. Confirmed via a real (non-dry-run) `pip install` + real `import` in this sandbox, not just `--dry-run` — no C-extension compilation occurred anywhere in the dependency tree (`lxml`/`numpy` resolved to already-present prebuilt wheels, `llvmlite` had a real `cp314` wheel, `pillow`/`opencv` don't even appear in this dependency graph since `unstructured`'s base install — no OCR extras — doesn't pull them in). This prerequisite is closed; the packages are ready to use.

Concretely:
- PDF parsing via Unstructured.io (primary), with PyMuPDF as the rescue path for layouts Unstructured mangles; Word parsing via `python-docx`. OCR and complex-table extraction stay explicitly deferred, not part of this issue.
- Widen Issue 01's format gate so PDF/Word are accepted rather than rejected, reusing its chunk/embed/ACL-enrich/index/job-store steps unchanged.
- **When Unstructured's primary PDF parse fails and the PyMuPDF rescue path fires, write a `parser_fallback: true` flag into the job's `job_queue.payload`** via Issue 01's job-store port (found during risk review, 2026-07-15 — chosen over a Qdrant per-chunk payload field: the fallback decision is made once per document, not per page, so every chunk would carry an identical value either way; `retrieve/`/`rerank/`/`verify/` don't exist yet and aren't planned to read `job_queue`, so a Qdrant payload field would sit unused until Phase 3 at real spec-change cost — see `.scratch/document-ingest-pipeline/PRD.md`'s Further Notes for the full trade-off. `job_queue.payload` has no fixed-field contract, unlike Qdrant's NFR-003-locked chunk payload, so this needs no spec change). Omit the flag (or set `false`) when Unstructured's primary parse succeeds — absence/`false` must mean "not degraded," not "unknown."
- When the embedding service (TEI) is unreachable, the job requeues with **jittered exponential backoff** (Full Jitter: `base * 2**attempt` scaled by a random factor in `[0, 1]`, not a bare deterministic `2**attempt`) and stays visible at an ops-facing pending-equivalent phase with an incrementing retry count — it must never silently hang, appear stuck with no signal, or produce synchronized retry timestamps across multiple concurrently-backed-off jobs (found during risk review, 2026-07-15 — a non-jittered backoff risks a thundering-herd retry storm re-crashing a just-recovered, still-fragile TEI instance).

## Acceptance criteria

- [ ] A text-extractable PDF upload reaches the pipeline's `ready` phase with correctly populated chunk payloads
      Verification: `pytest tests/ingest/test_pipeline.py -k pdf_happy_path` → passes
- [ ] A `.docx` upload reaches the pipeline's `ready` phase with correctly populated chunk payloads
      Verification: `pytest tests/ingest/test_pipeline.py -k docx_happy_path` → passes
- [ ] A PDF layout that fails Unstructured.io's primary parse falls back to PyMuPDF, still reaches `ready`, and the job's `job_queue.payload` carries `parser_fallback: true`; a normal (non-fallback) parse leaves it `false`/absent
      Verification: `pytest tests/ingest/test_pipeline.py -k pdf_rescue_path` → passes. **Flagged during `/verifiable-acceptance-criteria` (2026-07-14)**: whether a real PDF fixture that reliably fails Unstructured's parser but succeeds via PyMuPDF can be constructed on the first attempt is unverified — Unstructured's failure heuristics are internal and version-drifting. If no such fixture proves reliably constructible during implementation, fall back to mocking Unstructured's parse call to raise directly (asserting the rescue path activates and completes), rather than blocking the AC on finding a naturally-occurring malformed file
- [ ] A simulated embedding-service outage causes the job to requeue with backoff, remaining visible with an incrementing retry count, and never hangs indefinitely; retry delays are jittered, not deterministic — computing the backoff sequence for the same attempt count across multiple concurrently-retrying jobs does not produce identical delays
      Verification: `pytest tests/ingest/test_pipeline.py -k embedding_service_retry` → passes, using a fake TEI client configured to raise a transient connection error N times before succeeding; a second test (or a parametrized case in the same test) computes the backoff delay for the same attempt number across several simulated jobs and asserts the values are not all identical (found during risk review, 2026-07-15)

## Manual verification

- [ ] [manual-verify] A 100-page born-digital reference PDF reaches `ready` within 60 seconds on reference hardware (REQ-002's stated acceptance criterion, NFR-001's hardware floor).
      Owner: Backend / dev rig. Evidence to capture: timed end-to-end run against the real TEI/Qdrant/Postgres stack on the reference GPU rig, logged elapsed time.

## Blocked by

- Issue 01 (Plain-text/Markdown Ingest Pipeline) — reuses its chunk/embed/ACL-enrich/index/job-store machinery
