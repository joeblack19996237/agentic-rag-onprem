"""Runtime lookup of the active model version for a given role.

Added for the ingest pipeline's own need (TASK-008/009): naming the
target Qdrant collection via `ingest/qdrant_setup.py`'s
`build_collection_name(corpus_id, embedding_model_version)` requires
knowing which `embedding`-role model version is currently active. No
such query existed before this
(`.scratch/document-ingest-pipeline/issues/01-plaintext-markdown-ingest-pipeline.md`).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from config.models import ModelVersion


class NoActiveModelVersionError(LookupError):
    """Raised when no row is active for the given role -- every role
    (`generation`, `embedding`, `rerank`, `nli`, `safety_input`,
    `safety_output`, `policy`) is supposed to have exactly one active row
    per `specs/07-database.md`'s Seed Data section; a missing one means
    first-boot seeding never ran or the active flag was cleared."""


def get_active_model_version(session: Session, *, role: str) -> str:
    stmt = select(ModelVersion.model_version).where(ModelVersion.role == role, ModelVersion.is_active == True)  # noqa: E712 -- SQL WHERE clause, not a Python truthiness check
    result = session.execute(stmt).scalar_one_or_none()
    if result is None:
        raise NoActiveModelVersionError(f"No active model_versions row for role={role!r}")
    return result
