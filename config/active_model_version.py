"""Runtime lookup of the active model version for a given role.

Added for the ingest pipeline's own need (TASK-008/009): naming the
target Qdrant collection via `ingest/qdrant_setup.py`'s
`build_collection_name(corpus_id, embedding_model_version)` requires
knowing which `embedding`-role model version is currently active. No
such query existed before this
(`.scratch/document-ingest-pipeline/issues/01-plaintext-markdown-ingest-pipeline.md`).

`list_active_model_versions` (TASK-033 Issue 04) extends this into a
list-all-roles read for `GET /v1/admin/config/models` -- no new query
pattern, just `get_active_model_version` looped over `KNOWN_ROLES`, with
a per-role `NoActiveModelVersionError` caught and logged rather than
failing the whole request (a role that was never seeded is a real
misconfiguration an admin diagnostic endpoint should surface, not hide
behind a 500).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from config.models import ModelVersion

logger = logging.getLogger(__name__)

# Fixed, not derived (e.g. `SELECT DISTINCT role FROM model_versions`) --
# a role with no active row ever written would silently vanish from a
# dynamically-derived list, which is exactly the broken state this
# endpoint exists to surface. Per specs/07-database.md's Seed Data section.
KNOWN_ROLES = ["generation", "embedding", "rerank", "nli", "safety_input", "safety_output", "policy"]


class NoActiveModelVersionError(LookupError):
    """Raised when no row is active for the given role -- every role in
    `KNOWN_ROLES` is supposed to have exactly one active row per
    `specs/07-database.md`'s Seed Data section; a missing one means
    first-boot seeding never ran or the active flag was cleared."""


@dataclass(frozen=True)
class RoleModelVersion:
    role: str
    model_version: str | None


def get_active_model_version(session: Session, *, role: str) -> str:
    stmt = select(ModelVersion.model_version).where(ModelVersion.role == role, ModelVersion.is_active == True)  # noqa: E712 -- SQL WHERE clause, not a Python truthiness check
    result = session.execute(stmt).scalar_one_or_none()
    if result is None:
        raise NoActiveModelVersionError(f"No active model_versions row for role={role!r}")
    return result


def list_active_model_versions(session: Session) -> list[RoleModelVersion]:
    results = []
    for role in KNOWN_ROLES:
        try:
            model_version: str | None = get_active_model_version(session, role=role)
        except NoActiveModelVersionError:
            logger.warning("No active model_versions row for role=%r", role)
            model_version = None
        results.append(RoleModelVersion(role=role, model_version=model_version))
    return results
