"""Shared small value types for document identity and index targeting.

`(document_id, version_id)` travels together across `ingest/chunking.py`,
`acl/ingest_stub.py`, and `ingest/pipeline.py` -- bundled here so each
call site doesn't carry the pair as two loose parameters (code-review
finding, 2026-07-15). Lives in its own module rather than
`ingest/models.py` (ORM models only) or `ingest/pipeline.py` (would make
`acl/ingest_stub.py` depend on `ingest/pipeline.py`, which already
depends on `acl/ingest_stub.py` -- a real circular import)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentIdentity:
    document_id: uuid.UUID
    version_id: str
    repository_id: str


@dataclass(frozen=True)
class IndexTarget:
    collection_name: str
    embedding_model_version: str
