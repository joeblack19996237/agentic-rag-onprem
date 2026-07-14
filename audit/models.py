"""SQLAlchemy models for entities audit/ owns: audit_events,
legal_hold_invalidation_events. See specs/05-data-model.md's Field
Definitions and specs/07-database.md's Postgres Schema section for the
source of truth this mirrors.

`audit_events` immutability (DEC-070 -- no UPDATE/DELETE for the runtime
application role) is enforced at the database role level by the Alembic
migration's REVOKE statement, not expressible as an ORM-level constraint.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    audit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    query: Mapped[str] = mapped_column(nullable=False)
    # specs/05-data-model.md types this Array<String>, not JSON -- matching
    # document_versions.allow_principals/deny_principals' treatment of the
    # same declared type elsewhere in this schema.
    retrieved_chunk_ids: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    answer_text: Mapped[str] = mapped_column(nullable=False)
    citations: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    retrieval_safety_verdicts: Mapped[list[dict[str, object]] | None] = mapped_column(
        JSONB, nullable=True
    )
    safety_input_verdict: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    safety_output_verdict: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    verification_result: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    refusal_reason_actual: Mapped[str | None] = mapped_column(String, nullable=True)
    refusal_reason_shown: Mapped[str | None] = mapped_column(String, nullable=True)
    intent: Mapped[str] = mapped_column(String, nullable=False)
    context_fingerprint: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    revision_count: Mapped[int] = mapped_column(nullable=False, default=0)
    policy_waiver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    intent_class: Mapped[str | None] = mapped_column(String, nullable=True)
    nli_performed: Mapped[bool | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index("ix_audit_events_conversation_timestamp", "conversation_id", "timestamp"),
        Index("ix_audit_events_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_events_timestamp", "timestamp"),
    )


class LegalHoldInvalidationEvent(Base):
    __tablename__ = "legal_hold_invalidation_events"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    triggering_doc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    legal_hold_event_timestamp: Mapped[datetime] = mapped_column(nullable=False)
    invalidation_timestamp: Mapped[datetime] = mapped_column(nullable=False)
    invalidation_target: Mapped[str] = mapped_column(String, nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # specs/05-data-model.md types this Array<String>, not JSON -- see the
    # matching note on AuditEvent.retrieved_chunk_ids above.
    evicted_query_hashes: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    __table_args__ = (
        Index(
            "ix_legal_hold_invalidation_events_doc_timestamp",
            "triggering_doc_id",
            "invalidation_timestamp",
        ),
    )
