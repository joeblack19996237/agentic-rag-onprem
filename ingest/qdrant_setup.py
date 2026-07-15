"""Qdrant collection setup: creates the collection with dense+sparse vector
configuration and the 5 mandatory payload indexes, per
specs/07-database.md's Qdrant Collections section and
.scratch/data-foundation/issues/02-qdrant-collection-payload-indexes.md.

Payload-index *existence* cannot be verified against `qdrant_client.QdrantClient(":memory:")`
-- local mode silently no-ops `create_payload_index()` (specs/13-decision-log.md
DEC-140/DEC-141) -- so this module's own test suite checks that the index-creation
calls are made correctly (a call-inspection proxy), not that indexes exist on
disk. Real existence is `[manual-verify]` against a live server.
"""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    SparseVectorParams,
    VectorParams,
)
from sqlalchemy.orm import Session

from config.active_model_version import get_active_model_version
from ingest.identity import IndexTarget

# bge-m3's dense output is a fixed 1024-dimension vector (verified live,
# huggingface.co/BAAI/bge-m3, 2026-07-14 -- not training-data recall).
DENSE_VECTOR_SIZE = 1024
DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"

# Keyword indexes, per specs/07-database.md's Payload Indexes table.
MANDATORY_PAYLOAD_INDEXES = (
    "allow_principals",
    "deny_principals",
    "retention_state",
    "document_id",
    "security_label",
)


def build_collection_name(corpus_id: str, embedding_model_version: str) -> str:
    """`<corpus_id>_<embedding_model_version>` naming convention (DEC-059) --
    a new embedding-model version gets its own collection rather than
    mutating chunks in place, which is what makes blue/green re-embedding
    (REQ-034) possible later without a breaking migration."""
    return f"{corpus_id}_{embedding_model_version}"


def resolve_index_target(session: Session, corpus_id: str) -> IndexTarget:
    """Reads the active `embedding`-role model version
    (`config/active_model_version.py`) and builds the target collection
    name from it -- the concrete wiring that query exists to serve
    (code-review finding, 2026-07-15: the query had no real caller)."""
    embedding_model_version = get_active_model_version(session, role="embedding")
    return IndexTarget(
        collection_name=build_collection_name(corpus_id, embedding_model_version),
        embedding_model_version=embedding_model_version,
    )


def create_collection(client: QdrantClient, name: str) -> None:
    """Create `name` with dense+sparse vectors, then create all 5 mandatory
    payload indexes. Not idempotent against an existing collection of the
    same name -- recreating is the caller's responsibility (matches this
    issue's own Rollback Plan: drop and recreate, not upsert)."""
    client.create_collection(
        collection_name=name,
        vectors_config={
            DENSE_VECTOR_NAME: VectorParams(size=DENSE_VECTOR_SIZE, distance=Distance.COSINE)
        },
        sparse_vectors_config={SPARSE_VECTOR_NAME: SparseVectorParams()},
    )
    for field_name in MANDATORY_PAYLOAD_INDEXES:
        client.create_payload_index(
            collection_name=name,
            field_name=field_name,
            field_schema=PayloadSchemaType.KEYWORD,
        )
