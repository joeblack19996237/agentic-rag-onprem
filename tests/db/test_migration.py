"""Verifies the hand-authored Alembic migration (alembic/versions/0001_*.py)
against .scratch/data-foundation/issues/01-postgres-schema-migration.md's
acceptance criteria, using Alembic's offline `--sql` mode -- no live Postgres
connection is available in this environment (docs/agents/dev-environment.md),
and `--autogenerate` cannot run here either (same doc's Alembic row), so
these tests are the actual, repeatable definition of "the migration is
correct" until a live-Postgres run happens (that part stays [manual-verify],
per the issue's own Manual Verification section).
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_TABLES = [
    "documents",
    "document_versions",
    "job_queue",
    "audit_events",
    "legal_hold_invalidation_events",
    "model_versions",
    "prompt_templates",
    "eval_runs",
    "otel_spans",
]


def _run_alembic_raw(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", "-m", "alembic", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_alembic(*args: str) -> str:
    result = _run_alembic_raw(*args)
    result.check_returncode()
    return result.stdout


def test_upgrade_renders_all_nine_tables_offline():
    output = _run_alembic("upgrade", "head", "--sql")
    for table in EXPECTED_TABLES:
        assert f"CREATE TABLE {table} (" in output, f"missing CREATE TABLE for {table}"


def test_upgrade_document_versions_fk_has_no_cascade():
    output = _run_alembic("upgrade", "head", "--sql")
    assert (
        "FOREIGN KEY(document_id) REFERENCES documents (document_id) ON DELETE RESTRICT"
        in output
    )
    assert "ON DELETE CASCADE" not in output


def test_upgrade_job_queue_has_status_check_constraint():
    output = _run_alembic("upgrade", "head", "--sql")
    assert (
        "CONSTRAINT ck_job_queue_status CHECK "
        "(status IN ('pending', 'in_progress', 'complete', 'failed'))" in output
    )


def test_upgrade_model_versions_has_one_active_per_role_partial_index():
    output = _run_alembic("upgrade", "head", "--sql")
    assert (
        "CREATE UNIQUE INDEX ix_model_versions_one_active_per_role "
        "ON model_versions (role) WHERE is_active = true;" in output
    )


def test_upgrade_revokes_update_delete_on_audit_events():
    output = _run_alembic("upgrade", "head", "--sql")
    assert "REVOKE UPDATE, DELETE ON audit_events FROM app_runtime_role;" in output


def test_upgrade_array_typed_fields_are_not_jsonb():
    """specs/05-data-model.md types audit_events.retrieved_chunk_ids and
    legal_hold_invalidation_events.evicted_query_hashes as Array<String> --
    a code-review pass caught these initially rendered as JSONB instead,
    inconsistent with how document_versions.allow_principals/deny_principals
    (the same declared type, two tables earlier in this same file) were
    correctly rendered as arrays."""
    output = _run_alembic("upgrade", "head", "--sql")
    assert "retrieved_chunk_ids VARCHAR[] NOT NULL" in output
    assert "evicted_query_hashes VARCHAR[]" in output


def test_downgrade_drops_all_nine_tables_offline():
    output = _run_alembic("downgrade", "0001:base", "--sql")
    for table in EXPECTED_TABLES:
        assert f"DROP TABLE {table};" in output, f"missing DROP TABLE for {table}"


def test_bare_downgrade_base_fails_offline_without_explicit_revision_range():
    """Documents a real Alembic gotcha hit twice this session (main session +
    an independent re-check agent): offline mode needs `<fromrev>:<torev>`,
    not the bare target `alembic downgrade base --sql` that works online."""
    result = _run_alembic_raw("downgrade", "base", "--sql")
    assert result.returncode != 0
    assert "requires <fromrev>:<torev>" in result.stdout
