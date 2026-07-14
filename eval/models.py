"""SQLAlchemy model for the entity eval/ owns: eval_runs. See
specs/05-data-model.md's Field Definitions and specs/07-database.md's
Postgres Schema section for the source of truth this mirrors.

Field named `pass` in the spec prose is `passed` here -- `pass` is a Python
keyword and cannot be a mapped attribute name; nothing external depends on
the literal column name, so renaming both the attribute and the column is
the cleanest fix rather than fighting the keyword collision.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class EvalRun(Base):
    __tablename__ = "eval_runs"

    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    suite: Mapped[str] = mapped_column(nullable=False)
    metrics: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    model_versions_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    passed: Mapped[bool] = mapped_column("passed", nullable=False)
    run_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (Index("ix_eval_runs_suite_run_at", "suite", "run_at"),)
