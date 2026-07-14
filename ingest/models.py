"""SQLAlchemy models for entities ingest/ owns: documents, document_versions,
job_queue. See specs/05-data-model.md's Entity Overview "Owner" column and
specs/07-database.md's Postgres Schema section for the source of truth this
mirrors -- this file is a parallel ORM definition, not machine-derived from
the hand-authored Alembic migration (`alembic revision --autogenerate` cannot
run in this environment, see docs/agents/dev-environment.md's Alembic row).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    repository_id: Mapped[str] = mapped_column(String, nullable=False)
    parent_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # V2-reserved (REQ-006c access-request workflow); null-allowed, no
    # functional use yet -- specs/05-data-model.md's Field Definitions still
    # names them, so present-but-unused here rather than silently absent.
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approver_user_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    lifecycle_state: Mapped[str] = mapped_column(String, nullable=False, default="active")
    authority_state: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index("ix_documents_repository_document", "repository_id", "document_id", unique=True),
        Index("ix_documents_parent_document_id", "parent_document_id"),
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.document_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    version_id: Mapped[str] = mapped_column(String, primary_key=True)
    is_committed: Mapped[bool] = mapped_column(nullable=False, default=False)
    security_label: Mapped[str] = mapped_column(String, nullable=False)
    retention_state: Mapped[str] = mapped_column(String, nullable=False, default="active")
    allow_principals: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    deny_principals: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    superseded_by_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index("ix_document_versions_document_committed", "document_id", "is_committed"),
        Index("ix_document_versions_allow_principals", "allow_principals", postgresql_using="gin"),
        Index("ix_document_versions_deny_principals", "deny_principals", postgresql_using="gin"),
    )


class JobQueue(Base):
    __tablename__ = "job_queue"

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    locked_until: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'complete', 'failed')",
            name="ck_job_queue_status",
        ),
        Index("ix_job_queue_status_locked_until", "status", "locked_until"),
    )
