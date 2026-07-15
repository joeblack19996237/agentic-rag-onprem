"""Token-windowed text splitting and chunk_id identity.

1024 tokens / 128-token overlap per `specs/13-decision-log.md` DEC-065.
`chunk_id` is derived deterministically from `(document_id, version_id,
sequence)` via `uuid.uuid5` and must never be reassigned once a chunk
exists -- citation and audit records depend on it staying stable, and
Qdrant's point-upsert idempotency (a re-ingest of the same tuple
overwrites rather than duplicates, `specs/07-database.md`) depends on it
too. `uuid5` rather than a hash digest because Qdrant point IDs must be
an unsigned int or a UUID, not an arbitrary string.

Scope note: this is a token-window splitter (tokenize once, slide a
fixed-size window with overlap), not the paragraph/sentence-boundary-aware
recursive splitter the PRD's Implementation Decisions describe as the
eventual strategy -- no acceptance criterion in this issue tests boundary
placement, only token-derived sizing and chunk_id stability, so the
simpler, more precisely testable window approach is in scope here and the
boundary-aware refinement is left as a future improvement.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from ingest.identity import DocumentIdentity
from ingest.tokenizer import TextTokenizer

CHUNK_SIZE_TOKENS = 1024
CHUNK_OVERLAP_TOKENS = 128

_CHUNK_ID_NAMESPACE = uuid.UUID("d94a6b3e-9f1a-4c1e-8b1a-0f2f6a2e5c11")


@dataclass(frozen=True)
class Chunk:
    chunk_id: uuid.UUID
    sequence: int
    text: str


def build_chunk_id(document_id: uuid.UUID, version_id: str, sequence: int) -> uuid.UUID:
    name = f"{document_id}:{version_id}:{sequence}"
    return uuid.uuid5(_CHUNK_ID_NAMESPACE, name)


def split_into_chunks(
    text: str,
    *,
    identity: DocumentIdentity,
    tokenizer: TextTokenizer,
    size: int = CHUNK_SIZE_TOKENS,
    overlap: int = CHUNK_OVERLAP_TOKENS,
) -> list[Chunk]:
    if not text:
        return []
    token_ids = tokenizer.encode(text)
    if not token_ids:
        return []

    step = size - overlap
    chunks: list[Chunk] = []
    sequence = 0
    start = 0
    while start < len(token_ids):
        window = token_ids[start : start + size]
        chunks.append(
            Chunk(
                chunk_id=build_chunk_id(identity.document_id, identity.version_id, sequence),
                sequence=sequence,
                text=tokenizer.decode(window),
            )
        )
        sequence += 1
        start += step
    return chunks
