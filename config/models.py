"""SQLAlchemy models for entities config/ owns: model_versions,
prompt_templates. See specs/05-data-model.md's Field Definitions and
specs/07-database.md's Postgres Schema section for the source of truth
this mirrors.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    role: Mapped[str] = mapped_column(String, primary_key=True)
    model_version: Mapped[str] = mapped_column(String, primary_key=True)
    adapter_name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=False)
    activated_at: Mapped[datetime] = mapped_column(nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    pre_swap_ragas_report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_model_versions_one_active_per_role",
            "role",
            unique=True,
            postgresql_where=(is_active == True),  # noqa: E712 -- SQL WHERE clause, not a Python truthiness check
        ),
    )


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    prompt_template_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    version: Mapped[int] = mapped_column(nullable=False)
    body: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (Index("ix_prompt_templates_customer_version", "customer_id", "version"),)
