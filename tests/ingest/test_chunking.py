"""Tests for ingest/chunking.py -- token-windowed splitting and chunk_id
identity (DEC-065)."""

from __future__ import annotations

import uuid

from ingest.chunking import CHUNK_OVERLAP_TOKENS, CHUNK_SIZE_TOKENS, build_chunk_id, split_into_chunks
from ingest.identity import DocumentIdentity
from ingest.tokenizer import FakeTokenizer


def test_build_chunk_id_is_deterministic() -> None:
    doc_id = uuid.uuid4()
    first = build_chunk_id(doc_id, "v1", 0)
    second = build_chunk_id(doc_id, "v1", 0)
    assert first == second


def test_build_chunk_id_differs_by_sequence() -> None:
    doc_id = uuid.uuid4()
    assert build_chunk_id(doc_id, "v1", 0) != build_chunk_id(doc_id, "v1", 1)


def test_build_chunk_id_differs_by_version() -> None:
    doc_id = uuid.uuid4()
    assert build_chunk_id(doc_id, "v1", 0) != build_chunk_id(doc_id, "v2", 0)


def test_build_chunk_id_differs_by_document() -> None:
    assert build_chunk_id(uuid.uuid4(), "v1", 0) != build_chunk_id(uuid.uuid4(), "v1", 0)


def test_build_chunk_id_is_a_valid_uuid() -> None:
    # Qdrant point IDs must be an unsigned int or a UUID -- an arbitrary
    # string (e.g. a raw hash hex digest) is not a valid point ID.
    result = build_chunk_id(uuid.uuid4(), "v1", 0)
    assert isinstance(result, uuid.UUID)


def test_split_into_chunks_respects_size_and_overlap() -> None:
    tokenizer = FakeTokenizer()
    text = " ".join(f"word{i}" for i in range(10))
    identity = DocumentIdentity(document_id=uuid.uuid4(), version_id="v1", repository_id="default")
    chunks = split_into_chunks(text, identity=identity, tokenizer=tokenizer, size=4, overlap=1)
    # step = size - overlap = 3; windows start at 0, 3, 6, 9 -> 4 chunks
    assert [c.text for c in chunks] == [
        "word0 word1 word2 word3",
        "word3 word4 word5 word6",
        "word6 word7 word8 word9",
        "word9",
    ]
    assert [c.sequence for c in chunks] == [0, 1, 2, 3]


def test_split_into_chunks_produces_stable_chunk_ids_matching_build_chunk_id() -> None:
    tokenizer = FakeTokenizer()
    doc_id = uuid.uuid4()
    identity = DocumentIdentity(document_id=doc_id, version_id="v1", repository_id="default")
    chunks = split_into_chunks("a b c d e", identity=identity, tokenizer=tokenizer, size=2, overlap=0)
    assert chunks[0].chunk_id == build_chunk_id(doc_id, "v1", 0)
    assert chunks[1].chunk_id == build_chunk_id(doc_id, "v1", 1)


def test_split_into_chunks_empty_text_produces_no_chunks() -> None:
    tokenizer = FakeTokenizer()
    identity = DocumentIdentity(document_id=uuid.uuid4(), version_id="v1", repository_id="default")
    chunks = split_into_chunks("", identity=identity, tokenizer=tokenizer)
    assert chunks == []


def test_default_size_and_overlap_match_dec_065() -> None:
    assert CHUNK_SIZE_TOKENS == 1024
    assert CHUNK_OVERLAP_TOKENS == 128
