Status: ready-for-human

<!-- 2026-07-11: all 4 agent-checkable acceptance criteria are done and verified (see checkmarks below). Only the 3 [manual-verify] items remain (Docker daemon config check, vLLM on a CUDA host, llama-cpp-python on a host with a C/C++ toolchain) — moved to ready-for-human since nothing left is agent-closeable in this environment. -->

# Issue 01: Project Scaffold + Dependency Verification

> Source: `specs/10-build-plan.md` TASK-001 (Project Scaffold) + TASK-002 (Dependency Verification + Install), Phase 1. Traces to NFR-001, NFR-011, REQ-011 and DEC-033, DEC-034, DEC-035, DEC-075, DEC-076, DEC-012 (dependency version pins).
>
> **Correction (2026-07-08, DEC-131)**: LangGraph's pinned version below updated from "0.2.x" to "1.2.x" — 0.2.x was already stale when DEC-075 set it (verified via `gh api repos/langchain-ai/langgraph/releases`); see `specs/13-decision-log.md` DEC-131. Not yet implemented, so corrected in place rather than filed as a follow-up.
>
> **Addition (2026-07-08, DEC-133)**: `llama-cpp-python` added to the dependency pin list below. DEC-130 (RAGAS judge model, `Qwen2.5-14B-Instruct` via `llama.cpp`) had never been propagated into this task's dependency list — the package isn't actually *used* until Phase 5 (TASK-029), but this task pins every core dependency regardless of which phase first consumes it, the same way it already pins vLLM/TEI/Qdrant client ahead of their own later-phase use. See `specs/13-decision-log.md` DEC-133.
>
> **Correction (2026-07-11, agent environment check)**: `llama-cpp-python` moved out of the CPU-installable acceptance criteria and into `[manual-verify]`, matching the existing vLLM/Docker pattern below. Reason: PyPI's latest release (`0.3.33`) ships only a 67 MB sdist — no prebuilt wheel for any platform — so `pip install` falls through to a from-source build of `llama.cpp` itself, which requires a C/C++ toolchain (cmake + MSVC or gcc). The current agent execution environment was checked directly and has none of these (`cmake`, `cl.exe`, `gcc` all absent). This is a build-toolchain gap, not a dependency-resolution conflict — bundling it with the other CPU-installable pins would make a real "zero conflicts" pass unverifiable, since a from-source build failure and a resolver conflict look identical in a naive "did `pip install` exit 0" check. `specs/10-build-plan.md` TASK-002's own acceptance criteria stay generic ("every pinned dependency importable"); this split is an issue-level (environment-specific) refinement, the same way vLLM/Docker's manual-verify status never propagated up into the abstract spec task.
>
> **Correction (2026-07-11, independent AC re-check)**: the compose-file acceptance criterion below previously said "validate structure against the Compose Spec schema" without naming which schema file or which validator library — an unspecified check that could silently pass or fail differently depending on what the implementing agent happened to reach for. Rewritten to name a concrete, reproducible command: vendor the official Compose Spec JSON schema into the repo once, then validate with the `jsonschema` library (already available on PyPI, `>=3.10` Python compatible). This removes the ambiguity the same way the `llama-cpp-python` correction above did — the fix pattern is "name the exact tool," not "assume a schema check happens somehow."
>
> **Correction (2026-07-11, DEC-134)**: Python version updated from "3.12" to "3.14" below. Not a fix to a prior error — DEC-033's original 3.12 pin was deliberate and correct when made. This is a fresh re-decision: the actual agent execution environment for this Phase 1 work only has Python 3.14.3 installed (no 3.12 runtime present), and rather than install a second runtime, the target was re-pinned to match. All 7 CPU-installable dependencies below were verified compatible with 3.14.3 (zero-conflict `pip install --dry-run`, live PyPI metadata) before this change was made. See `specs/13-decision-log.md` DEC-134.
>
> **Progress (2026-07-11, dependency half of TASK-002 completed ahead of `/implement`)**: the two CPU-installable-dependency acceptance criteria below are already done and checked off, with evidence — do not re-run this work from scratch. [requirements.txt](../../../requirements.txt) (7 core pins) and [requirements-llama-cpp.txt](../../../requirements-llama-cpp.txt) (isolated, `[manual-verify]`) already exist at the repo root. `pip install --dry-run -r requirements.txt` resolved with zero conflicts, and a smoke-import of all 7 (`fastapi`, `uvicorn`, `langgraph`, `qdrant_client`, `psycopg`, `redis`, `yaml`) exited 0. What's still genuinely unstarted is TASK-001's half: no module directories exist yet (`api/`, `retrieve/`, ... all missing) and no docker-compose skeleton file exists yet — `/implement` should focus there.

## What to build

Set up the project's directory scaffold and docker-compose skeleton matching the module map in `specs/04-architecture.md` §5, then pin and verify every core dependency the rest of the system will build on.

Scaffold: create a placeholder directory (with `__init__.py`) for every module in the module map — `api/`, `retrieve/`, `acl/`, `rerank/`, `generate/`, `verify/`, `audit/`, `ingest/`, `admin/`, `eval/`, `config/`, `widget/`, `cdc/`, `safety_input/`, `safety_output/`, `policy/`, `cache/` — plus a `docker-compose` skeleton for the services these modules will eventually run against.

Dependency pinning: pin exact versions for Python 3.14, FastAPI, LangGraph 1.2.x, vLLM, TEI client, Qdrant client, Postgres driver, Redis client, and `llama-cpp-python`, per the decision log's pinned choices (DEC-033, DEC-075, DEC-012, DEC-035, DEC-034, DEC-076; LangGraph version corrected DEC-131; `llama-cpp-python` added DEC-133; Python version re-pinned 3.12→3.14 DEC-134). Verify every pinned dependency is importable.

Both halves are TDD-Exempt (Infrastructure-as-Code / vendor-SDK installation, per `spec-templates.md`'s exempt-type table) — there is no red→green→refactor cycle for "does the directory exist" or "does the dependency import cleanly." Verification is a config/command check, not a test suite.

## Acceptance criteria

- [x] Every module directory from §5's module map exists with a placeholder `__init__.py`
      Verification: `find api retrieve acl rerank generate verify audit ingest admin eval config widget cdc safety_input safety_output policy cache -name __init__.py` → one result per module, none missing
      **Done (2026-07-11)**: all 17 directories created with `__init__.py`; `find` command above returned exactly 17 results, none missing.
- [x] Compose skeleton file passes structural validation against the Compose Spec, without requiring a Docker daemon
      Verification, two steps: (1) vendor the official Compose Spec JSON schema into the repo once, e.g. `schemas/compose-spec.schema.json`, sourced from `https://raw.githubusercontent.com/compose-spec/compose-spec/master/schema/compose-spec.json` and committed — so later runs don't depend on network access; (2) `pip install pyyaml jsonschema` (if not already present), then `python -c "import yaml, json, jsonschema; jsonschema.validate(instance=yaml.safe_load(open('<compose file path>')), schema=json.load(open('schemas/compose-spec.schema.json')))"` → completes with no exception raised = pass; a raised `jsonschema.exceptions.ValidationError` (schema violation) or `yaml.YAMLError` (parse failure) = fail
      **Done (2026-07-11)**: `docker-compose.yml` created at repo root (12 services per `04-architecture.md` §9.1: api, vllm, tei-embed, tei-rerank, nli, safety-input, safety-output, policy, qdrant, postgres, redis, widget). Schema vendored to `schemas/compose-spec.schema.json`. Validation script ran with no exception raised — pass.
- [x] CPU-installable pinned dependencies (FastAPI, LangGraph 1.2.x, TEI client, Qdrant client, Postgres driver, Redis client) install with zero conflicts
      Verification: `pip install <requirements file>` → exit code 0, no resolver conflict output. Note: the Postgres driver may need libpq headers to build from source on some hosts — prefer a prebuilt/binary wheel pin so a missing system library doesn't read as a false "conflict". `llama-cpp-python` is excluded from this list — see `[manual-verify]` below.
      **Done (2026-07-11)**: `pip install --dry-run -r requirements.txt` → resolver succeeded, zero conflicts, all 8 pins resolved (fastapi==0.135.2, uvicorn==0.42.0, langgraph==1.2.9, httpx==0.28.1, qdrant-client==1.18.0, psycopg[binary]==3.3.4, redis==8.0.1, PyYAML==6.0.3). **Correction (code-review finding)**: TEI has no dedicated PyPI client package — `httpx` was initially left as an implicit, unpinned transitive dependency of `qdrant-client` and the AC was checked off without a real pin backing "TEI client." Fixed: `httpx==0.28.1` now pinned explicitly in `requirements.txt` as the TEI client, re-verified zero-conflict.
- [x] CPU-installable pinned dependencies are importable in a smoke-import script
      Verification: `python -c "import <name>"` for each CPU-installable pin (use the exact import name from the dependency table this task produces) → exits 0 for every one. `llama-cpp-python` is excluded from this list — see `[manual-verify]` below.
      **Done (2026-07-11)**: `python -c "import fastapi, uvicorn, langgraph, httpx, qdrant_client, psycopg, redis, yaml"` (via `importlib.import_module` loop) → all 8 imported successfully, exit 0.

## Manual verification (if any)

- [ ] [manual-verify] `docker compose config` validates the full compose file against a live Docker daemon, without error
      Owner: DevOps (or whoever has Docker available). Evidence to capture: command output showing the resolved config, or the error if it fails. Docker is confirmed unavailable in the current agent execution environment (`docker: command not found`) — the schema-level check above is the closest agent-groundable proxy; this item is the final word and can't be closed by the agent.
- [ ] [manual-verify] vLLM installs and imports cleanly
      Owner: DevOps/AI (needs a CUDA-capable host). Evidence to capture: install log + `python -c "import vllm"` output from that host. No GPU is present in the current agent execution environment (`nvidia-smi: command not found`) — this can't be closed by the agent.
- [ ] [manual-verify] `llama-cpp-python==0.3.33` (or the then-current pin) installs and imports cleanly
      Owner: DevOps/Backend (needs a host with a C/C++ build toolchain — cmake + MSVC on Windows, or gcc/clang on Linux/macOS — since PyPI ships no prebuilt wheel as of 0.3.33). Evidence to capture: install log + `python -c "import llama_cpp"` output from that host. The current agent execution environment was checked directly and has none of `cmake`, `cl.exe`, or `gcc` — this can't be closed by the agent as-is.

## Blocked by

None - can start immediately
