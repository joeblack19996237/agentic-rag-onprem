"""Directly-callable ingest pipeline entry point: parse (.md/.txt/.pdf/.docx)
-> chunk -> embed -> Layer 1 ACL enrichment -> Qdrant index write.

Not an HTTP route -- `POST /v1/ingest` doesn't exist until `TASK-033`
wires a route to this pipeline later
(`.scratch/document-ingest-pipeline/issues/01-plaintext-markdown-ingest-pipeline.md`).

Each step persists its output to a checkpoint file (`ingest/checkpoints.py`)
and advances a lightweight phase/progress pointer in the job-store
(`ingest/job_store.py`) before the next step starts. Re-invoking
`resume_ingest_job` for a `job_id` whose earlier steps already completed
skips redoing them; the embed+index step is not skip-based -- it relies
on Qdrant's own upsert-by-`chunk_id` idempotency (deterministic point
IDs, `ingest/chunking.py`) to make a redundant retry safe rather than
tracking a separate "already indexed" flag.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, cast

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, SparseVector

from acl.ingest_stub import ACLLookup
from ingest.checkpoints import DEFAULT_CHECKPOINT_DIR, read_checkpoint, write_checkpoint
from ingest.chunking import split_into_chunks
from ingest.embedding import EmbeddingClient, EmbeddingResult
from ingest.identity import DocumentIdentity, IndexTarget
from ingest.job_store import JobPhase, JobStore
from ingest.parsing import SUPPORTED_EXTENSIONS, DocumentDecodeError, UnsupportedFormatError, parse_document
from ingest.qdrant_setup import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
from ingest.retry import compute_backoff_delay
from ingest.tokenizer import TextTokenizer

__all__ = [
    "DocumentDecodeError",
    "PipelineDependencies",
    "SUPPORTED_EXTENSIONS",
    "UnsupportedFormatError",
    "ingest_document",
    "resume_ingest_job",
]

# Bounds the embedding-service retry loop so an unreachable TEI never
# hangs a job indefinitely -- it fails cleanly (ops-visible via
# job_store.fail()) once exhausted, per Issue 02's risk review.
MAX_EMBEDDING_RETRY_ATTEMPTS = 5


@dataclass
class PipelineDependencies:
    tokenizer: TextTokenizer
    job_store: JobStore
    acl_lookup: ACLLookup
    embedding_client: EmbeddingClient
    qdrant_client: QdrantClient
    checkpoint_dir: Path = DEFAULT_CHECKPOINT_DIR
    sleep: Callable[[float], None] = time.sleep


def ingest_document(
    file_bytes: bytes,
    filename: str,
    *,
    identity: DocumentIdentity,
    target: IndexTarget,
    deps: PipelineDependencies,
) -> uuid.UUID:
    """Starts a new ingest job and runs it to completion (or fails it).
    Format is validated before any job row is created."""
    if not filename.lower().endswith(SUPPORTED_EXTENSIONS):
        raise UnsupportedFormatError(
            f"Unsupported format: {filename!r}. Supported: {SUPPORTED_EXTENSIONS}"
        )
    job_id = deps.job_store.create_job("ingest")
    _run_pipeline(job_id, file_bytes, filename, identity, target, deps)
    return job_id


def resume_ingest_job(
    job_id: uuid.UUID,
    file_bytes: bytes,
    filename: str,
    *,
    identity: DocumentIdentity,
    target: IndexTarget,
    deps: PipelineDependencies,
) -> None:
    """Re-invokes the pipeline for an already-created `job_id`, resuming
    from its last completed step rather than restarting. `file_bytes`/
    `filename` are only actually used if parsing hasn't completed yet --
    a resume past the "parsed" phase reads the checkpoint file instead."""
    _run_pipeline(job_id, file_bytes, filename, identity, target, deps)


def _run_pipeline(
    job_id: uuid.UUID,
    file_bytes: bytes,
    filename: str,
    identity: DocumentIdentity,
    target: IndexTarget,
    deps: PipelineDependencies,
) -> None:
    try:
        payload = deps.job_store.get_payload(job_id)
        phase = cast("JobPhase", payload.get("phase", "pending"))

        if phase == "pending":
            payload = _run_parse_step(job_id, file_bytes, filename, deps)
            phase = cast("JobPhase", payload["phase"])

        if phase == "parsed":
            payload = _run_chunk_step(job_id, identity, payload, deps)
            phase = cast("JobPhase", payload["phase"])

        if phase in ("chunked", "indexing"):
            _run_embed_and_index_step(job_id, identity, target, payload, deps)

        deps.job_store.complete(job_id)
    except Exception as exc:
        deps.job_store.fail(job_id, str(exc))
        raise


def _run_parse_step(
    job_id: uuid.UUID, file_bytes: bytes, filename: str, deps: PipelineDependencies
) -> dict[str, Any]:
    result = parse_document(file_bytes, filename)

    payload_updates: dict[str, object] = {"phase": "parsed", "progress": 0.2}
    # parser_fallback only applies to PDF (the only format with a rescue
    # tier) -- absent for .md/.txt/.docx, where the concept doesn't exist.
    if result.used_fallback_parser is not None:
        payload_updates["parser_fallback"] = result.used_fallback_parser

    checkpoint_path = write_checkpoint(deps.checkpoint_dir, job_id, "parsed", {"text": result.text})
    payload_updates["parsed_checkpoint_path"] = checkpoint_path
    deps.job_store.advance(job_id, payload_updates)
    return deps.job_store.get_payload(job_id)


def _run_chunk_step(
    job_id: uuid.UUID, identity: DocumentIdentity, payload: dict[str, Any], deps: PipelineDependencies
) -> dict[str, Any]:
    # write_checkpoint always serializes a dict (see _run_parse_step /
    # _run_embed_and_index_step) -- read_checkpoint's return type stays
    # `object` because it's a generic JSON round-trip, not a lie about
    # what any *particular* checkpoint file actually holds.
    parsed = cast("dict[str, Any]", read_checkpoint(payload["parsed_checkpoint_path"]))
    chunks = split_into_chunks(parsed["text"], identity=identity, tokenizer=deps.tokenizer)
    chunk_dicts = [
        {"chunk_id": str(c.chunk_id), "sequence": c.sequence, "text": c.text} for c in chunks
    ]
    checkpoint_path = write_checkpoint(deps.checkpoint_dir, job_id, "chunked", {"chunks": chunk_dicts})
    deps.job_store.advance(
        job_id, {"phase": "chunked", "progress": 0.4, "chunked_checkpoint_path": checkpoint_path}
    )
    return deps.job_store.get_payload(job_id)


def _run_embed_and_index_step(
    job_id: uuid.UUID,
    identity: DocumentIdentity,
    target: IndexTarget,
    payload: dict[str, Any],
    deps: PipelineDependencies,
) -> None:
    # ACL lookup is fail-closed by construction: an exception here
    # propagates out of _run_pipeline (via the caller's try/except,
    # which marks the job failed and re-raises) before any chunk is
    # written -- a chunk is never indexed without its ACL payload.
    acl = deps.acl_lookup.get_effective_acl(identity)
    retention_state = deps.acl_lookup.get_retention_state(identity)

    chunked = cast("dict[str, Any]", read_checkpoint(payload["chunked_checkpoint_path"]))
    chunk_dicts = cast("list[dict[str, Any]]", chunked["chunks"])
    chunk_texts = [c["text"] for c in chunk_dicts]

    # NFR-012: only chunk text goes to the embedding call -- ACL/identity
    # fields are attached to the payload below, never mixed into the
    # text sent for embedding.
    embeddings = _embed_with_retry(job_id, chunk_texts, deps)

    deps.job_store.advance(job_id, {"phase": "indexing", "progress": 0.7})

    points = [
        PointStruct(
            id=chunk_dict["chunk_id"],
            vector={
                DENSE_VECTOR_NAME: embedding.dense,
                SPARSE_VECTOR_NAME: SparseVector(
                    indices=embedding.sparse_indices, values=embedding.sparse_values
                ),
            },
            payload={
                "document_id": str(identity.document_id),
                "version_id": identity.version_id,
                "repository_id": identity.repository_id,
                "chunk_id": chunk_dict["chunk_id"],
                "sequence": chunk_dict["sequence"],
                "text": chunk_dict["text"],
                "embedding_model_version": target.embedding_model_version,
                "allow_principals": acl.allow_principals,
                "deny_principals": acl.deny_principals,
                "security_label": acl.security_label,
                "retention_state": retention_state,
                "frozen_at": None,
            },
        )
        for chunk_dict, embedding in zip(chunk_dicts, embeddings, strict=True)
    ]
    # Qdrant upsert is idempotent by chunk_id -- a redundant retry after
    # a crash between this write and the checkpoint advance overwrites
    # rather than duplicates (risk review, 2026-07-15).
    deps.qdrant_client.upsert(collection_name=target.collection_name, points=points)


def _embed_with_retry(
    job_id: uuid.UUID, chunk_texts: list[str], deps: PipelineDependencies
) -> list[EmbeddingResult]:
    """Retries the embedding call with Full Jitter backoff (`ingest/retry.py`)
    when the embedding service (TEI) is unreachable -- `httpx.TransportError`,
    a connection failure, not an HTTP error response (a real 4xx/5xx from a
    reachable TEI is not transient and propagates immediately). Bounded by
    MAX_EMBEDDING_RETRY_ATTEMPTS so an outage never hangs the job indefinitely;
    once exhausted, the last error propagates and `_run_pipeline` marks the
    job failed.

    `job_queue.payload["phase"]` is deliberately left untouched here (still
    "chunked", set by the prior step) rather than reset to a "pending"-like
    value -- doing so would break `_run_pipeline`'s resume dispatch (a crash
    mid-retry, then `resume_ingest_job`, would re-run `_run_parse_step`,
    which needs the original file bytes again). The incrementing
    `retry_count` field is the ops-visible signal instead.

    This blocks the calling thread for the backoff duration (`deps.sleep`,
    real `time.sleep` in production) rather than releasing the job back to
    a dispatcher for another worker to pick up -- Issue 02's own text calls
    this "requeues", which could read as the latter. No dispatcher/worker
    pool exists anywhere in this codebase yet (`ingest_document`/
    `resume_ingest_job` are directly-callable synchronous functions, per
    this module's own top docstring -- `POST /v1/ingest` isn't wired until
    TASK-033), so an in-process bounded retry is what's actually buildable
    at this issue's scope; a real cross-process requeue (DEC-038's
    `SELECT ... FOR UPDATE SKIP LOCKED` pattern releasing the job for
    another poll cycle) is a design this codebase doesn't have the
    infrastructure for yet. Also worth knowing: this retries the whole
    `embed()` call, so a sparse-only failure redundantly recomputes an
    already-succeeded dense result on each retry -- see
    `HybridTEIEmbeddingClient.embed()`'s own docstring for that trade-off
    (external peer review, 2026-07-15, low severity, not fixed). Revisit
    this function once a real dispatcher
    exists (code-review finding, 2026-07-15).
    """
    attempt = 0
    while True:
        try:
            return deps.embedding_client.embed(chunk_texts)
        except httpx.TransportError:
            attempt += 1
            if attempt > MAX_EMBEDDING_RETRY_ATTEMPTS:
                raise
            deps.job_store.advance(job_id, {"retry_count": attempt})
            deps.sleep(compute_backoff_delay(attempt))
