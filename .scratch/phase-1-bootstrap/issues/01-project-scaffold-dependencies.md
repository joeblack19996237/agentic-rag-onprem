Status: ready-for-agent

# Issue 01: Project Scaffold + Dependency Verification

> Source: `specs/10-build-plan.md` TASK-001 (Project Scaffold) + TASK-002 (Dependency Verification + Install), Phase 1. Traces to NFR-001, NFR-011, REQ-011 and DEC-033, DEC-034, DEC-035, DEC-075, DEC-076, DEC-012 (dependency version pins).
>
> **Correction (2026-07-08, DEC-131)**: LangGraph's pinned version below updated from "0.2.x" to "1.2.x" — 0.2.x was already stale when DEC-075 set it (verified via `gh api repos/langchain-ai/langgraph/releases`); see `specs/13-decision-log.md` DEC-131. Not yet implemented, so corrected in place rather than filed as a follow-up.
>
> **Addition (2026-07-08, DEC-133)**: `llama-cpp-python` added to the dependency pin list below. DEC-130 (RAGAS judge model, `Qwen2.5-14B-Instruct` via `llama.cpp`) had never been propagated into this task's dependency list — the package isn't actually *used* until Phase 5 (TASK-029), but this task pins every core dependency regardless of which phase first consumes it, the same way it already pins vLLM/TEI/Qdrant client ahead of their own later-phase use. See `specs/13-decision-log.md` DEC-133.

## What to build

Set up the project's directory scaffold and docker-compose skeleton matching the module map in `specs/04-architecture.md` §5, then pin and verify every core dependency the rest of the system will build on.

Scaffold: create a placeholder directory (with `__init__.py`) for every module in the module map — `api/`, `retrieve/`, `acl/`, `rerank/`, `generate/`, `verify/`, `audit/`, `ingest/`, `admin/`, `eval/`, `config/`, `widget/`, `cdc/`, `safety_input/`, `safety_output/`, `policy/`, `cache/` — plus a `docker-compose` skeleton for the services these modules will eventually run against.

Dependency pinning: pin exact versions for Python 3.12, FastAPI, LangGraph 1.2.x, vLLM, TEI client, Qdrant client, Postgres driver, Redis client, and `llama-cpp-python`, per the decision log's pinned choices (DEC-033, DEC-075, DEC-012, DEC-035, DEC-034, DEC-076; LangGraph version corrected DEC-131; `llama-cpp-python` added DEC-133). Verify every pinned dependency is importable.

Both halves are TDD-Exempt (Infrastructure-as-Code / vendor-SDK installation, per `spec-templates.md`'s exempt-type table) — there is no red→green→refactor cycle for "does the directory exist" or "does the dependency import cleanly." Verification is a config/command check, not a test suite.

## Acceptance criteria

- [ ] Every module directory from §5's module map exists with a placeholder `__init__.py`
      Verification: `find api retrieve acl rerank generate verify audit ingest admin eval config widget cdc safety_input safety_output policy cache -name __init__.py` → one result per module, none missing
- [ ] Compose skeleton file passes structural validation against the Compose Spec, without requiring a Docker daemon
      Verification: parse with PyYAML (`pip install pyyaml` if not already present) and validate structure against the Compose Spec schema, e.g. `python -c "import yaml; yaml.safe_load(open('<compose file path>'))"` plus a schema check → no parse error, no schema violation
- [ ] CPU-installable pinned dependencies (FastAPI, LangGraph 1.2.x, TEI client, Qdrant client, Postgres driver, Redis client, `llama-cpp-python`) install with zero conflicts
      Verification: `pip install <requirements file>` → exit code 0, no resolver conflict output. Note: the Postgres driver may need libpq headers to build from source on some hosts — prefer a prebuilt/binary wheel pin so a missing system library doesn't read as a false "conflict".
- [ ] CPU-installable pinned dependencies are importable in a smoke-import script
      Verification: `python -c "import <name>"` for each CPU-installable pin (use the exact import name from the dependency table this task produces) → exits 0 for every one

## Manual verification (if any)

- [ ] [manual-verify] `docker compose config` validates the full compose file against a live Docker daemon, without error
      Owner: DevOps (or whoever has Docker available). Evidence to capture: command output showing the resolved config, or the error if it fails. Docker is confirmed unavailable in the current agent execution environment (`docker: command not found`) — the schema-level check above is the closest agent-groundable proxy; this item is the final word and can't be closed by the agent.
- [ ] [manual-verify] vLLM installs and imports cleanly
      Owner: DevOps/AI (needs a CUDA-capable host). Evidence to capture: install log + `python -c "import vllm"` output from that host. No GPU is present in the current agent execution environment (`nvidia-smi: command not found`) — this can't be closed by the agent.

## Blocked by

None - can start immediately
