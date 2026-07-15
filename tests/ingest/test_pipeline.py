"""Tests for ingest/pipeline.py against the 8 acceptance criteria in
`.scratch/document-ingest-pipeline/issues/01-plaintext-markdown-ingest-pipeline.md`.

Uses QdrantClient(":memory:") (real client, embedded local mode --
DEC-140/DEC-141) plus the in-memory/fake job-store, ACL lookup,
tokenizer, and embedding client -- no live Postgres/TEI needed, per
DEC-135's Tier-1 default.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import SparseVector

from acl.ingest_stub import ACLLookupError, EffectiveACL, FakeACLLookup
from ingest.embedding import EmbeddingResult, FakeEmbeddingClient
from ingest.identity import DocumentIdentity, IndexTarget
from ingest.job_store import InMemoryJobStore
from ingest.pipeline import (
    PipelineDependencies,
    UnsupportedFormatError,
    ingest_document,
    resume_ingest_job,
)
from ingest.qdrant_setup import build_collection_name, create_collection
from ingest.tokenizer import FakeTokenizer

NFR_003_FIELDS = frozenset(
    {
        "document_id",
        "version_id",
        "repository_id",
        "chunk_id",
        "sequence",
        "text",
        "embedding_model_version",
        "allow_principals",
        "deny_principals",
        "security_label",
        "retention_state",
        "frozen_at",
    }
)


def _make_deps(tmp_path: Path, qdrant: QdrantClient) -> PipelineDependencies:
    return PipelineDependencies(
        tokenizer=FakeTokenizer(),
        job_store=InMemoryJobStore(),
        acl_lookup=FakeACLLookup(),
        embedding_client=FakeEmbeddingClient(),
        qdrant_client=qdrant,
        checkpoint_dir=tmp_path,
    )


def _make_identity() -> DocumentIdentity:
    return DocumentIdentity(document_id=uuid.uuid4(), version_id="v1", repository_id="default")


def _make_target(qdrant: QdrantClient) -> IndexTarget:
    collection_name = build_collection_name("default", "bge-m3-v2")
    create_collection(qdrant, collection_name)
    return IndexTarget(collection_name=collection_name, embedding_model_version="bge-m3-v2")


def _seed_acl(deps: PipelineDependencies, identity: DocumentIdentity) -> None:
    assert isinstance(deps.acl_lookup, FakeACLLookup)
    deps.acl_lookup.seed(
        identity,
        acl=EffectiveACL(
            allow_principals=["group:eng"], deny_principals=["user:contractor-42"], security_label="internal"
        ),
        retention_state="active",
    )


# --- AC: happy_path ----------------------------------------------------


def test_happy_path_md_upload_reaches_ready_with_full_payload_and_both_vectors(tmp_path: Path) -> None:
    qdrant = QdrantClient(":memory:")
    deps = _make_deps(tmp_path, qdrant)
    identity = _make_identity()
    target = _make_target(qdrant)
    _seed_acl(deps, identity)

    job_id = ingest_document(
        b"# Title\n\nSome markdown body text.", "notes.md", identity=identity, target=target, deps=deps
    )

    assert deps.job_store.get_status(job_id) == "complete"
    assert deps.job_store.get_payload(job_id)["phase"] == "ready"

    points = qdrant.scroll(collection_name=target.collection_name, with_vectors=True, with_payload=True)[0]
    assert len(points) > 0
    for point in points:
        assert point.payload is not None
        assert point.payload["allow_principals"] == ["group:eng"]
        assert point.payload["deny_principals"] == ["user:contractor-42"]
        assert point.payload["security_label"] == "internal"
        assert point.payload["retention_state"] == "active"
        assert isinstance(point.vector, dict)
        dense_vector = point.vector["dense"]
        sparse_vector = point.vector["sparse"]
        assert isinstance(dense_vector, list)
        assert len(dense_vector) > 0
        assert isinstance(sparse_vector, SparseVector)
        assert len(sparse_vector.indices) > 0


def test_happy_path_txt_upload_also_supported(tmp_path: Path) -> None:
    qdrant = QdrantClient(":memory:")
    deps = _make_deps(tmp_path, qdrant)
    identity = _make_identity()
    target = _make_target(qdrant)
    _seed_acl(deps, identity)

    job_id = ingest_document(b"plain text content", "notes.txt", identity=identity, target=target, deps=deps)

    assert deps.job_store.get_status(job_id) == "complete"


# --- AC: unsupported_format ---------------------------------------------


@pytest.mark.parametrize("filename", ["report.pdf", "memo.docx", "image.png", "noextension"])
def test_unsupported_format_rejected_with_no_job_created(tmp_path: Path, filename: str) -> None:
    qdrant = QdrantClient(":memory:")
    deps = _make_deps(tmp_path, qdrant)
    identity = _make_identity()
    target = _make_target(qdrant)

    calls: list[str] = []
    original_create_job = deps.job_store.create_job

    def spying_create_job(job_type: str) -> uuid.UUID:
        calls.append(job_type)
        return original_create_job(job_type)

    deps.job_store.create_job = spying_create_job  # type: ignore[method-assign]

    with pytest.raises(UnsupportedFormatError):
        ingest_document(b"irrelevant bytes", filename, identity=identity, target=target, deps=deps)

    assert calls == []


# --- AC: nfr_012 ----------------------------------------------------------


def test_nfr_012_embedding_input_never_contains_acl_or_identity_fields(tmp_path: Path) -> None:
    qdrant = QdrantClient(":memory:")
    deps = _make_deps(tmp_path, qdrant)
    identity = _make_identity()
    target = _make_target(qdrant)
    _seed_acl(deps, identity)

    captured_texts: list[str] = []
    original_embed = deps.embedding_client.embed

    def spying_embed(texts: list[str]) -> list[EmbeddingResult]:
        captured_texts.extend(texts)
        return original_embed(texts)

    deps.embedding_client.embed = spying_embed  # type: ignore[method-assign]

    ingest_document(
        b"# Doc\n\nBody mentioning nothing secret.", "notes.md", identity=identity, target=target, deps=deps
    )

    assert captured_texts, "embed() was never called"
    for text in captured_texts:
        assert "group:eng" not in text
        assert "contractor-42" not in text
        assert "allow_principals" not in text
        assert "deny_principals" not in text


# --- AC: chunk_immutability ------------------------------------------------


def test_chunk_immutability_same_document_version_sequence_yields_same_chunk_id(tmp_path: Path) -> None:
    qdrant = QdrantClient(":memory:")
    deps_a = _make_deps(tmp_path, qdrant)
    identity = _make_identity()
    target = _make_target(qdrant)
    _seed_acl(deps_a, identity)

    ingest_document(b"repeatable content", "a.md", identity=identity, target=target, deps=deps_a)
    points_first = qdrant.scroll(collection_name=target.collection_name, with_payload=True)[0]
    first_id = points_first[0].id

    # Re-ingesting the identical (document_id, version_id) content again
    # must produce the same chunk_id, not a new one.
    deps_b = _make_deps(tmp_path, qdrant)
    _seed_acl(deps_b, identity)
    ingest_document(b"repeatable content", "a.md", identity=identity, target=target, deps=deps_b)

    points_second = qdrant.scroll(collection_name=target.collection_name, with_payload=True)[0]
    assert len(points_second) == len(points_first)
    assert points_second[0].id == first_id


# --- AC: checkpoint_idempotency -------------------------------------------


def test_checkpoint_idempotency_resume_skips_already_completed_parse_and_chunk(tmp_path: Path) -> None:
    qdrant = QdrantClient(":memory:")
    deps = _make_deps(tmp_path, qdrant)
    identity = _make_identity()
    target = _make_target(qdrant)
    _seed_acl(deps, identity)

    job_id = deps.job_store.create_job("ingest")
    # Simulate parse+chunk already having completed in an earlier,
    # interrupted call.
    from ingest.checkpoints import write_checkpoint
    from ingest.chunking import split_into_chunks

    text = "some earlier-parsed content"
    parsed_path = write_checkpoint(tmp_path, job_id, "parsed", {"text": text})
    deps.job_store.advance(job_id, {"phase": "parsed", "progress": 0.2, "parsed_checkpoint_path": parsed_path})
    chunks = split_into_chunks(text, identity=identity, tokenizer=deps.tokenizer)
    chunk_dicts = [{"chunk_id": str(c.chunk_id), "sequence": c.sequence, "text": c.text} for c in chunks]
    chunked_path = write_checkpoint(tmp_path, job_id, "chunked", {"chunks": chunk_dicts})
    deps.job_store.advance(job_id, {"phase": "chunked", "progress": 0.4, "chunked_checkpoint_path": chunked_path})

    calls: list[list[str]] = []
    original_embed = deps.embedding_client.embed

    def counting_embed(texts: list[str]) -> list[EmbeddingResult]:
        calls.append(texts)
        return original_embed(texts)

    deps.embedding_client.embed = counting_embed  # type: ignore[method-assign]

    resume_ingest_job(job_id, b"unused, parse already checkpointed", identity=identity, target=target, deps=deps)

    assert deps.job_store.get_status(job_id) == "complete"
    # embed was called exactly once (for the embed+index step) -- parse
    # and chunk were not redone, only the remaining step ran.
    assert len(calls) == 1


def test_checkpoint_idempotency_retry_after_qdrant_write_relies_on_upsert(tmp_path: Path) -> None:
    """The named risk-review scenario: Qdrant write already succeeded but
    the job-store phase was never advanced past "indexing" (simulating a
    crash between the two) -- retrying must not produce extra points."""
    qdrant = QdrantClient(":memory:")
    deps = _make_deps(tmp_path, qdrant)
    identity = _make_identity()
    target = _make_target(qdrant)
    _seed_acl(deps, identity)

    # First call runs the full pipeline to completion normally.
    job_id = ingest_document(b"content for retry test", "a.md", identity=identity, target=target, deps=deps)
    points_after_first = qdrant.scroll(collection_name=target.collection_name, with_payload=True)[0]
    point_count_after_first = len(points_after_first)
    assert point_count_after_first > 0

    # Force the job-store back to "indexing" (as if the completion
    # checkpoint never landed), then resume with the same inputs.
    deps.job_store.advance(job_id, {"phase": "indexing", "progress": 0.7})
    resume_ingest_job(job_id, b"content for retry test", identity=identity, target=target, deps=deps)

    points_after_retry = qdrant.scroll(collection_name=target.collection_name, with_payload=True)[0]
    assert len(points_after_retry) == point_count_after_first


# --- AC: acl_lookup_failure_blocks -----------------------------------------


def test_acl_lookup_failure_blocks_ingest_and_writes_no_chunk(tmp_path: Path) -> None:
    qdrant = QdrantClient(":memory:")
    deps = _make_deps(tmp_path, qdrant)
    identity = _make_identity()
    target = _make_target(qdrant)
    # Deliberately not seeded -- FakeACLLookup raises ACLLookupError.

    with pytest.raises(ACLLookupError):
        ingest_document(b"content", "a.md", identity=identity, target=target, deps=deps)

    points = qdrant.scroll(collection_name=target.collection_name, with_payload=True)[0]
    assert points == []


# --- AC: nfr_003_field_names ------------------------------------------------


def test_nfr_003_chunk_payload_field_names_match_documented_set_exactly(tmp_path: Path) -> None:
    qdrant = QdrantClient(":memory:")
    deps = _make_deps(tmp_path, qdrant)
    identity = _make_identity()
    target = _make_target(qdrant)
    _seed_acl(deps, identity)

    ingest_document(b"content for field-name check", "a.md", identity=identity, target=target, deps=deps)

    points = qdrant.scroll(collection_name=target.collection_name, with_payload=True)[0]
    assert points
    for point in points:
        assert point.payload is not None
        assert frozenset(point.payload.keys()) == NFR_003_FIELDS


# --- AC: job_payload_stays_lightweight --------------------------------------


def test_job_payload_stays_lightweight_never_holds_raw_text_or_chunks(tmp_path: Path) -> None:
    qdrant = QdrantClient(":memory:")
    deps = _make_deps(tmp_path, qdrant)
    identity = _make_identity()
    target = _make_target(qdrant)
    _seed_acl(deps, identity)

    long_text = "word " * 5000  # large enough that stuffing it into
    # job_queue.payload directly would be an obvious red flag
    job_id = ingest_document(long_text.encode("utf-8"), "big.md", identity=identity, target=target, deps=deps)

    payload = deps.job_store.get_payload(job_id)
    allowed_keys = {"phase", "progress", "parsed_checkpoint_path", "chunked_checkpoint_path"}
    assert set(payload.keys()) <= allowed_keys
    for key, value in payload.items():
        if isinstance(value, str):
            assert len(value) < 500, f"{key} looks like it holds bulk content, not a pointer: {value[:80]}..."
        assert long_text not in str(value)
