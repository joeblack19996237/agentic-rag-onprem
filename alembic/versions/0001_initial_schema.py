"""Initial schema: all 9 Postgres tables from specs/07-database.md.

Hand-authored using Alembic's op.* DSL, not `alembic revision --autogenerate`
-- that command hard-requires a live database connection to diff against
(confirmed unavailable in this environment, docs/agents/dev-environment.md's
Alembic row). Kept in parallel with, and consistent with, each owning
module's SQLAlchemy models (ingest/models.py, audit/models.py,
config/models.py, eval/models.py, api/models.py) -- this file is what
Alembic actually executes; the models are what application code queries
through.

Revision ID: 0001
Revises:
Create Date: 2026-07-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# The application's runtime database role -- created and granted elsewhere
# in the customer's install runbook (specs/09-deployment-ops.md), not by
# this migration. Named here only as the target of the REVOKE below.
RUNTIME_ROLE = "app_runtime_role"


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("repository_id", sa.String(), nullable=False),
        sa.Column("parent_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        # V2-reserved (REQ-006c access-request workflow); null-allowed, no
        # functional use yet -- kept in parallel with ingest/models.py's
        # Document model rather than silently omitted.
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "approver_user_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True
        ),
        sa.Column("lifecycle_state", sa.String(), nullable=False, server_default="active"),
        sa.Column("authority_state", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_documents_repository_document",
        "documents",
        ["repository_id", "document_id"],
        unique=True,
    )
    op.create_index("ix_documents_parent_document_id", "documents", ["parent_document_id"])

    op.create_table(
        "document_versions",
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.document_id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("version_id", sa.String(), primary_key=True),
        sa.Column("is_committed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("security_label", sa.String(), nullable=False),
        sa.Column("retention_state", sa.String(), nullable=False, server_default="active"),
        sa.Column(
            "allow_principals",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "deny_principals",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("superseded_by_version_id", sa.String(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_document_versions_document_committed",
        "document_versions",
        ["document_id", "is_committed"],
    )
    op.create_index(
        "ix_document_versions_allow_principals",
        "document_versions",
        ["allow_principals"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_document_versions_deny_principals",
        "document_versions",
        ["deny_principals"],
        postgresql_using="gin",
    )

    op.create_table(
        "job_queue",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'complete', 'failed')",
            name="ck_job_queue_status",
        ),
    )
    op.create_index("ix_job_queue_status_locked_until", "job_queue", ["status", "locked_until"])

    op.create_table(
        "audit_events",
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        # specs/05-data-model.md types this Array<String>, not JSON.
        sa.Column("retrieved_chunk_ids", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), nullable=False),
        sa.Column("retrieval_safety_verdicts", postgresql.JSONB(), nullable=True),
        sa.Column("safety_input_verdict", postgresql.JSONB(), nullable=True),
        sa.Column("safety_output_verdict", postgresql.JSONB(), nullable=True),
        sa.Column("verification_result", postgresql.JSONB(), nullable=False),
        sa.Column("refusal_reason_actual", sa.String(), nullable=True),
        sa.Column("refusal_reason_shown", sa.String(), nullable=True),
        sa.Column("intent", sa.String(), nullable=False),
        sa.Column("context_fingerprint", postgresql.JSONB(), nullable=False),
        sa.Column("revision_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("policy_waiver_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("intent_class", sa.String(), nullable=True),
        sa.Column("nli_performed", sa.Boolean(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_audit_events_conversation_timestamp",
        "audit_events",
        ["conversation_id", "timestamp"],
    )
    op.create_index("ix_audit_events_user_timestamp", "audit_events", ["user_id", "timestamp"])
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"])
    # DEC-070: audit_events is append-only forever. Enforced at the database
    # role level, not just application discipline -- the runtime role can
    # INSERT/SELECT but never UPDATE or DELETE this table.
    op.execute(f"REVOKE UPDATE, DELETE ON audit_events FROM {RUNTIME_ROLE}")

    op.create_table(
        "legal_hold_invalidation_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("triggering_doc_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("legal_hold_event_timestamp", sa.DateTime(), nullable=False),
        sa.Column("invalidation_timestamp", sa.DateTime(), nullable=False),
        sa.Column("invalidation_target", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=True),
        # specs/05-data-model.md types this Array<String>, not JSON.
        sa.Column("evicted_query_hashes", postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.create_index(
        "ix_legal_hold_invalidation_events_doc_timestamp",
        "legal_hold_invalidation_events",
        ["triggering_doc_id", "invalidation_timestamp"],
    )

    op.create_table(
        "model_versions",
        sa.Column("role", sa.String(), primary_key=True),
        sa.Column("model_version", sa.String(), primary_key=True),
        sa.Column("adapter_name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("activated_at", sa.DateTime(), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
        sa.Column("pre_swap_ragas_report_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # DEC-... (07-database.md Constraints): partial unique index enforces
    # "exactly one active row per role" at the database level.
    op.create_index(
        "ix_model_versions_one_active_per_role",
        "model_versions",
        ["role"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    op.create_table(
        "prompt_templates",
        sa.Column("prompt_template_id", sa.String(), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_prompt_templates_customer_version", "prompt_templates", ["customer_id", "version"]
    )

    op.create_table(
        "eval_runs",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("suite", sa.String(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("model_versions_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("run_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_eval_runs_suite_run_at", "eval_runs", ["suite", "run_at"])

    op.create_table(
        "otel_spans",
        sa.Column("span_id", sa.String(), primary_key=True),
        sa.Column("trace_id", sa.String(), nullable=False),
        sa.Column("parent_span_id", sa.String(), nullable=True),
        sa.Column("node_name", sa.String(), nullable=False),
        sa.Column("attributes", postgresql.JSONB(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_otel_spans_trace_id", "otel_spans", ["trace_id"])
    op.create_index("ix_otel_spans_timestamp", "otel_spans", ["timestamp"])


def downgrade() -> None:
    op.drop_table("otel_spans")
    op.drop_table("eval_runs")
    op.drop_table("prompt_templates")
    op.drop_index("ix_model_versions_one_active_per_role", table_name="model_versions")
    op.drop_table("model_versions")
    op.drop_table("legal_hold_invalidation_events")
    op.execute(f"GRANT UPDATE, DELETE ON audit_events TO {RUNTIME_ROLE}")
    op.drop_table("audit_events")
    op.drop_table("job_queue")
    op.drop_table("document_versions")
    op.drop_table("documents")
