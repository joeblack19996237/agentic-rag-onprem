Status: ready-for-human

# Issue 01: Postgres Schema Migration

> Source: `specs/10-build-plan.md` TASK-006 (Phase 2). Traces to `specs/02-requirements.md` REQ-007, REQ-034, REQ-035 and `specs/13-decision-log.md` DEC-059, DEC-060. Physical schema source: `specs/07-database.md`. Verification Pattern: TDD-Exempt — DB schema migration.

## Parent

None — traces directly to `specs/10-build-plan.md` TASK-006, no parent issue.

## What to build

Alembic-managed SQLAlchemy schema for all 9 Postgres tables in `specs/07-database.md`'s Postgres Schema section: `documents`, `document_versions`, `audit_events`, `legal_hold_invalidation_events`, `model_versions`, `prompt_templates`, `eval_runs`, `job_queue`, `otel_spans`, with their stated primary keys, foreign keys, check constraints, and indexes.

Models live in each entity's owning module, per `specs/05-data-model.md`'s Entity Overview "Owner" column: `ingest/` owns `documents`, `document_versions`, `job_queue`; `audit/` owns `audit_events`, `legal_hold_invalidation_events`; `config/` owns `model_versions`, `prompt_templates`; `eval/` owns `eval_runs`; `api/` owns `otel_spans`.

**The shared SQLAlchemy declarative Base plus engine/session setup must NOT live in `config/`** — a prior draft of this issue said it should, which is wrong and was caught by an independent re-check (confirmed by hand, 2026-07-14): `tests/architecture/import_graph.py`'s `FORBIDDEN_IMPORTS["eval"]` is a blanket ban on importing *any* other first-party module (same treatment as `rerank/`/`widget/` — modules that must reach the rest of the system only through an external interface, per `specs/04-architecture.md` §5.1), and `eval/` is one of this issue's own five owning modules. Putting the shared Base/engine in `config/` would make `eval/`'s models import `config/` to get it, which trips this exact check — reproduced directly: dropping a one-line `import config` probe into `eval/` and running `check_import_graph()` produces `` eval\_tmp_import_probe.py: `eval/` imports forbidden module `config/` `` — and this check runs inside `bash tools/verify.sh` and pre-commit, so it would fail after the fact, not be caught by any of this issue's own acceptance criteria below.

Instead, put the shared Base/engine/session in a new top-level `db/` directory, outside the pipeline module map entirely (the same category `tests/`, `tools/`, `docs/` already occupy — `tests/architecture/import_graph.py`'s `MODULES` set only contains the 17 named pipeline/domain modules from `specs/04-architecture.md` §5's module map, so a new non-pipeline infrastructure directory isn't subject to any module's forbidden-imports list). This correctly separates "shared persistence infrastructure every owning module needs direct DB access to" from "another pipeline module's business logic," which is what the call-direction rules are actually policing — `config/` itself is for configuration (YAML loading, model-version config), not general-purpose infrastructure, and conflating the two is what caused this conflict. A single top-level Alembic environment collects every module's model metadata (imported from each owning module plus `db/`) for one migration.

**The migration must be hand-authored using Alembic's `op.*` DSL, not machine-generated via `alembic revision --autogenerate`.** Confirmed in this repo's execution environment (`docs/agents/dev-environment.md`'s Alembic row): `--autogenerate` hard-requires a live database connection to reflect current schema state and diff against the models — it hangs or raises `OperationalError` here, since there is no live Postgres. `alembic upgrade head --sql` / `alembic downgrade <rev>:base --sql` (offline mode, dialect-targeted DDL rendering) work with zero live connection and are this issue's verification mechanism.

**`alembic.ini`'s `sqlalchemy.url` must be set to a `postgresql`-scheme URL** (e.g. `postgresql+psycopg://user:pass@localhost/dbname`) before running any offline `--sql` command — offline mode never connects to this URL, but its scheme is what selects the DDL dialect Alembic renders. Leaving Alembic's scaffolded default (`driver://user:pass@localhost/dbname`) or pointing it at a non-Postgres dialect would silently render the wrong DDL (no real error, just DDL that doesn't actually prove Postgres compatibility — e.g. a different dialect's partial-index/array-type syntax) — confirmed by hand this session, this is not obvious from Alembic's own `init` scaffold.

## Acceptance criteria

- [x] SQLAlchemy and Alembic are pinned in `requirements.txt` and importable
      Verification: `grep -E "^(SQLAlchemy|[Aa]lembic)==" requirements.txt` finds both lines, and `python -c "import sqlalchemy, alembic"` → exit 0
      **Done (2026-07-14)**: `SQLAlchemy==2.0.51` and `alembic==1.18.5` pinned in `requirements.txt` (live-verified via PyPI, `cp314`-compatible wheels confirmed installable). `python -c "import sqlalchemy, alembic, pytest_mock"` → `sqlalchemy 2.0.51`, `alembic 1.18.5`, exit 0.
- [x] The hand-authored migration renders correct DDL for all 9 tables with their stated constraints
      Verification: `alembic upgrade head --sql` (offline mode, `postgresql` dialect target, no live connection) → output contains 9 `CREATE TABLE` statements (one per table name above), the `document_versions.document_id → documents.document_id` foreign key with no `ON DELETE CASCADE`, `job_queue`'s `CHECK (status IN ('pending', 'in_progress', 'complete', 'failed'))`, and `model_versions`' partial unique index (`CREATE UNIQUE INDEX ... WHERE is_active = true` or equivalent)
      **Done (2026-07-14)**: `alembic/versions/0001_initial_schema.py` hand-authored with `op.*` calls for all 9 tables. `alembic upgrade head --sql` output confirmed via `pytest tests/db/test_migration.py -v` (7 tests, all pass) — 9 `CREATE TABLE` statements present, FK reads `ON DELETE RESTRICT` with no `CASCADE` anywhere in the output, `job_queue`'s exact CHECK text present, `model_versions`' `CREATE UNIQUE INDEX ix_model_versions_one_active_per_role ON model_versions (role) WHERE is_active = true;` present.
- [x] `audit_events` immutability is enforced at the database role level, not just application discipline
      Verification: the same `alembic upgrade head --sql` output contains a `REVOKE UPDATE, DELETE ON audit_events FROM <runtime_role>` statement (or equivalent role-scoped revoke)
      **Done (2026-07-14)**: output contains `REVOKE UPDATE, DELETE ON audit_events FROM app_runtime_role;` verbatim (`test_upgrade_revokes_update_delete_on_audit_events`, passing).
- [x] The migration is structurally reversible
      Verification: `alembic downgrade <revision>:base --sql` — note the explicit `<fromrev>:<torev>` form is required; bare `alembic downgrade base --sql` fails offline with `FAILED: downgrade with --sql requires <fromrev>:<torev>` (confirmed empirically this session) — generates valid `DROP TABLE` statements for all 9 tables with no error
      **Done (2026-07-14)**: `alembic downgrade 0001:base --sql` → 9 `DROP TABLE` statements (`ix_model_versions_one_active_per_role` dropped explicitly first), no error. Bare `alembic downgrade base --sql` confirmed to still fail with the documented message — both behaviors pinned by `test_downgrade_drops_all_nine_tables_offline` and `test_bare_downgrade_base_fails_offline_without_explicit_revision_range`, both passing.

This proves the migration's DDL content and structural reversibility, not that it actually runs against a real server — that gap is the manual-verify item below, matching `specs/13-decision-log.md` DEC-135's Tier 1/2 (agent-executable, offline rendering) vs. Tier 3 (live-service) split for this exact class of check.

## Manual verification

- [ ] [manual-verify] Migration runs clean against a live Postgres 16 instance in both directions (the true round-trip dry-run `specs/10-build-plan.md` TASK-006's own Verification Plan asks for — "dry-run against a staging snapshot"), and the `audit_events` REVOKE is actually enforced.
      Owner: DevOps / dev rig. Evidence to capture: `alembic upgrade head` output against a real Postgres 16, `alembic downgrade base` output confirming clean rollback, and the exact error text from an attempted `UPDATE`/`DELETE` on `audit_events` as the runtime application role (must fail with a permissions error, not merely an application-level refusal).

## Owner Role

Backend (per `specs/10-build-plan.md` TASK-006)

## Rollback Plan

Alembic downgrade; re-run the offline `--sql` dry-run against the pre-migration state to confirm reversibility before this migration is ever run against a real database (per TASK-006's own Rollback Plan).

## Blocked by

None - can start immediately (TASK-001 already done)
