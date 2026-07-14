"""SQLAlchemy model for the entity api/ owns: otel_spans (all nodes emit
spans through api/, per specs/05-data-model.md's Entity Overview). See
specs/07-database.md's Postgres Schema section for the source of truth
this mirrors.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class OtelSpan(Base):
    __tablename__ = "otel_spans"

    span_id: Mapped[str] = mapped_column(String, primary_key=True)
    trace_id: Mapped[str] = mapped_column(String, nullable=False)
    parent_span_id: Mapped[str | None] = mapped_column(String, nullable=True)
    node_name: Mapped[str] = mapped_column(String, nullable=False)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index("ix_otel_spans_trace_id", "trace_id"),
        Index("ix_otel_spans_timestamp", "timestamp"),
    )
