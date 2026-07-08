Status: ready-for-agent

# Issue 01: Project Scaffold + Dependency Verification

> Source: `specs/10-build-plan.md` TASK-001 (Project Scaffold) + TASK-002 (Dependency Verification + Install), Phase 1. Traces to NFR-001, NFR-011, REQ-011 and DEC-033, DEC-034, DEC-035, DEC-075, DEC-076, DEC-012 (dependency version pins).

## What to build

Set up the project's directory scaffold and docker-compose skeleton matching the module map in `specs/04-architecture.md` §5, then pin and verify every core dependency the rest of the system will build on.

Scaffold: create a placeholder directory (with `__init__.py`) for every module in the module map — `api/`, `retrieve/`, `acl/`, `rerank/`, `generate/`, `verify/`, `audit/`, `ingest/`, `admin/`, `eval/`, `config/`, `widget/`, `cdc/`, `safety_input/`, `safety_output/`, `policy/`, `cache/` — plus a `docker-compose` skeleton for the services these modules will eventually run against.

Dependency pinning: pin exact versions for Python 3.12, FastAPI, LangGraph 0.2.x, vLLM, TEI client, Qdrant client, Postgres driver, and Redis client, per the decision log's pinned choices (DEC-033, DEC-075, DEC-012, DEC-035, DEC-034, DEC-076). Verify every pinned dependency is importable.

Both halves are TDD-Exempt (Infrastructure-as-Code / vendor-SDK installation, per `spec-templates.md`'s exempt-type table) — there is no red→green→refactor cycle for "does the directory exist" or "does the dependency import cleanly." Verification is a config/command check, not a test suite.

## Acceptance criteria

- [ ] `docker compose config` validates the compose file without error
- [ ] Every module directory from §5's module map exists with a placeholder `__init__.py`
- [ ] Dependency install (e.g. `pip install`) succeeds with zero conflicts
- [ ] Every pinned dependency is importable in a smoke-import script

## Blocked by

None - can start immediately
