"""Disposable, narrowly-scoped Layer 1 ACL/retention lookups for the
ingest pipeline.

Reads document_versions directly. This is NOT a forward-designed
ECMAdapter/LocalAdapter Protocol for TASK-013 (Phase 3's Layer 2 JIT
adapter) to reuse or extend -- acl/ has no real adapter code yet
(verified empty, 2026-07-14), and TASK-013 designs the real interface
independently and may replace this stub outright. Scoped to exactly the
two calls the ingest pipeline needs
(`.scratch/document-ingest-pipeline/issues/01-plaintext-markdown-ingest-pipeline.md`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from ingest.identity import DocumentIdentity
from ingest.models import DocumentVersion


class ACLLookupError(LookupError):
    """Raised when a document_versions row can't be found. The caller
    must block ingest rather than write a chunk with no ACL payload --
    fail-closed, not fail-open."""


@dataclass(frozen=True)
class EffectiveACL:
    allow_principals: list[str]
    deny_principals: list[str]
    security_label: str


class ACLLookup(Protocol):
    def get_effective_acl(self, identity: DocumentIdentity) -> EffectiveACL: ...

    def get_retention_state(self, identity: DocumentIdentity) -> str: ...


class SqlAlchemyACLLookup:
    """Real implementation, reading `document_versions` directly."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_effective_acl(self, identity: DocumentIdentity) -> EffectiveACL:
        version = self._fetch(identity)
        return EffectiveACL(
            allow_principals=list(version.allow_principals),
            deny_principals=list(version.deny_principals),
            security_label=version.security_label,
        )

    def get_retention_state(self, identity: DocumentIdentity) -> str:
        return self._fetch(identity).retention_state

    def _fetch(self, identity: DocumentIdentity) -> DocumentVersion:
        version = self._session.get(DocumentVersion, (identity.document_id, identity.version_id))
        if version is None:
            raise ACLLookupError(f"No document_versions row for ({identity.document_id}, {identity.version_id})")
        return version


class FakeACLLookup:
    """In-memory fake for tests -- pre-seeded per `(document_id,
    version_id)`. An unseeded lookup raises `ACLLookupError`, the same
    fail-closed behavior as a missing row in the real implementation --
    this doubles as the failure-simulation path for tests that need one,
    no separate "configure to raise" method required."""

    def __init__(self) -> None:
        self._acls: dict[tuple[str, str], EffectiveACL] = {}
        self._retention: dict[tuple[str, str], str] = {}

    def seed(self, identity: DocumentIdentity, *, acl: EffectiveACL, retention_state: str) -> None:
        key = (str(identity.document_id), identity.version_id)
        self._acls[key] = acl
        self._retention[key] = retention_state

    def get_effective_acl(self, identity: DocumentIdentity) -> EffectiveACL:
        key = (str(identity.document_id), identity.version_id)
        try:
            return self._acls[key]
        except KeyError:
            raise ACLLookupError(f"No seeded ACL for {key}") from None

    def get_retention_state(self, identity: DocumentIdentity) -> str:
        key = (str(identity.document_id), identity.version_id)
        try:
            return self._retention[key]
        except KeyError:
            raise ACLLookupError(f"No seeded retention state for {key}") from None
