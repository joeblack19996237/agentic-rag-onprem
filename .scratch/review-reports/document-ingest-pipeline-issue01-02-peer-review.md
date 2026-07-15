# Peer Review

**Date:** 2026-07-15
**Reviewer:** deepseek-v4-pro (different vendor family)
**Scope:** `076ce77..HEAD` (076ce77 → c1fe82d)
**Issues reviewed:** [01-plaintext-markdown-ingest-pipeline](../document-ingest-pipeline/issues/01-plaintext-markdown-ingest-pipeline.md) + [02-pdf-word-parsing-retry-resilience](../document-ingest-pipeline/issues/02-pdf-word-parsing-retry-resilience.md)
**Files reviewed:** 85 files, +5244 / −257 lines (core implementation: `ingest/`, `acl/`, `config/`, `db/`, `tests/`)

## P.1 [LOW] — Performance

File: [ingest/embedding.py:107-119](ingest/embedding.py#L107-L119)
Issue: `HybridTEIEmbeddingClient.embed()` calls `embed_dense` then `embed_sparse` sequentially. When the sparse TEI deployment is unreachable (while the dense one is healthy), the `httpx.TransportError` from `embed_sparse` triggers a full retry of the entire `embed()` call — the already-computed dense vectors are discarded and recomputed on each retry. With `MAX_EMBEDDING_RETRY_ATTEMPTS=5`, this is bounded to at most 5× redundant dense computation per job during a sparse-only outage.
Fix: Split the retry into independent dense/sparse calls, or cache the dense result from the first attempt and reuse it across retries. At minimum, swap the call order so the cheaper/more-likely-to-fail call runs first — if sparse embedding is more likely to be the bottleneck, call `embed_sparse` before `embed_dense`.

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH     | 0 |
| MEDIUM   | 0 |
| LOW      | 1 |

This is a clean, well-implemented diff covering both Phase 2 issues. Every acceptance criterion from Issue 01 (8 ACs) and Issue 02 (5 ACs, counting the jitter test) has a corresponding test, and the tests actually verify the claimed behavior — field-name sets are exact-match checked, chunk-id immutability is cross-run, the Qdrant-upsert idempotency scenario from risk review is explicitly simulated, and the embedding retry loop is bounded-then-fail proved (not just happy-path-succeeds proved). Security is clean across the board: no hardcoded secrets, database access is properly parameterized through the ORM, checkpoint paths are built from typed constants and UUIDs with no user-controlled surface, and the NFR-012 ACL/identity exclusion from embedding text is runtime-verified. The one LOW issue — redundant dense recomputation during a sparse-only TEI outage — is bounded and unlikely in practice (both TEI deployments likely share infrastructure), making this a genuine edge case rather than a common-path problem. Design quality is high: narrow Protocols for seams (`JobStore`, `ACLLookup`, `EmbeddingClient`, `TextTokenizer`), well-scoped modules with clear ownership, and thorough docstrings that flag known limitations (the sync retry vs. future dispatcher, error strings before an HTTP boundary, token-window vs. semantic chunking) rather than leaving them to be discovered later.

Verdict: **APPROVE**
