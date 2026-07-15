"""Directly-callable ingest pipeline entry point: parse (.md/.txt only)
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

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, SparseVector

from acl.ingest_stub import ACLLookup
from ingest.checkpoints import DEFAULT_CHECKPOINT_DIR, read_checkpoint, write_checkpoint
from ingest.chunking import split_into_chunks
from ingest.embedding import EmbeddingClient
from ingest.identity import DocumentIdentity, IndexTarget
from ingest.job_store import JobPhase, JobStore
from ingest.qdrant_setup import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
from ingest.tokenizer import TextTokenizer

SUPPORTED_EXTENSIONS = (".md", ".txt")


class UnsupportedFormatError(ValueError):
    """Raised for any upload whose extension isn't in
    SUPPORTED_EXTENSIONS -- PDF/Word included, until Issue 02 widens the
    accepted set. The caller (eventually TASK-033's HTTP layer) maps
    this to a 415."""


class DocumentDecodeError(ValueError):
    """Raised when the uploaded bytes aren't valid UTF-8 text -- wraps
    the raw UnicodeDecodeError so callers see a domain-level error, not
    an internal decoding detail (coding-standards.md's error-handling
    boundary rule)."""


@dataclass
class PipelineDependencies:
    tokenizer: TextTokenizer
    job_store: JobStore
    acl_lookup: ACLLookup
    embedding_client: EmbeddingClient
    qdrant_client: QdrantClient
    checkpoint_dir: Path = DEFAULT_CHECKPOINT_DIR


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
    _run_pipeline(job_id, file_bytes, identity, target, deps)
    return job_id


def resume_ingest_job(
    job_id: uuid.UUID,
    file_bytes: bytes,
    *,
    identity: DocumentIdentity,
    target: IndexTarget,
    deps: PipelineDependencies,
) -> None:
    """Re-invokes the pipeline for an already-created `job_id`, resuming
    from its last completed step rather than restarting."""
    _run_pipeline(job_id, file_bytes, identity, target, deps)


def _run_pipeline(
    job_id: uuid.UUID,
    file_bytes: bytes,
    identity: DocumentIdentity,
    target: IndexTarget,
    deps: PipelineDependencies,
) -> None:
    try:
        payload = deps.job_store.get_payload(job_id)
        phase = cast("JobPhase", payload.get("phase", "pending"))

        if phase == "pending":
            payload = _run_parse_step(job_id, file_bytes, deps)
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


def _run_parse_step(job_id: uuid.UUID, file_bytes: bytes, deps: PipelineDependencies) -> dict[str, Any]:
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentDecodeError(f"Upload is not valid UTF-8 text: {exc}") from exc

    checkpoint_path = write_checkpoint(deps.checkpoint_dir, job_id, "parsed", {"text": text})
    deps.job_store.advance(
        job_id, {"phase": "parsed", "progress": 0.2, "parsed_checkpoint_path": checkpoint_path}
    )
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
    embeddings = deps.embedding_client.embed(chunk_texts)

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
