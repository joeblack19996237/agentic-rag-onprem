# Phase 1 Handoff — GroundedDocs Bootstrap

> Written 2026-07-11 for a fresh session with zero context on the conversation that produced it. Read this before touching anything in this repo.

## What this project is

**GroundedDocs** — an on-prem, vendor-embeddable document Q&A agent for CCM/ECM vendors (Quadient, Smart Communications, M-Files, Hyland). Answers must be grounded in verified citations, with honest refusal when grounding is weak. Fully local LLM inference, no cloud egress.

- **Canonical source of truth**: `specs/` (entry point `specs/00-index.md`). Everything else supports producing/maintaining that spec set.
- **Decision log**: `specs/13-decision-log.md` — append-only, canonical over any conflicting prose elsewhere. If something looks inconsistent, the decision log wins.
- **Issue tracker**: local markdown under `.scratch/<feature>/issues/`, not GitHub Issues. See `docs/agents/issue-tracker.md`.
- **Repo**: `D:\AI\claude_code\agentic-rag-onprem`, pushed to `https://github.com/joeblack19996237/agentic-rag-onprem` (**public**, MIT-licensed).

## What we were doing this session

Executing **Phase 1 (bootstrap)** of `specs/10-build-plan.md`, tracked as three issues in `.scratch/phase-1-bootstrap/issues/`:

| Issue | What it covers | Status |
|---|---|---|
| `01-project-scaffold-dependencies.md` | 17 module scaffold dirs + core dependency pinning | ✅ Done, `ready-for-human` |
| `02-dev-rig-ci-baseline.md` | Architecture import-graph check + CI baseline | ✅ Done, `ready-for-human` |
| `03-first-failing-smoke-test.md` | Minimal `GET /ready` + first TDD red checkpoint | ✅ Done, `ready-for-human` |

**All agent-closeable acceptance criteria across all three issues are done and verified with real evidence — not just claimed.** Each issue file has inline `**Done (date)**` notes under every checked box showing the actual command run and its actual output. Read the issue files directly for the full evidence trail; this doc only summarizes.

Every issue is `ready-for-human`, not `ready-for-agent` or closed — each still has 1+ `[manual-verify]` item that needs infrastructure this environment doesn't have, or a NFR-011 item needing a live human trial. That's expected, not a gap.

## What's actually in the repo now

- 17 empty module dirs (`api/`, `retrieve/`, `acl/`, `rerank/`, `generate/`, `verify/`, `audit/`, `ingest/`, `admin/`, `eval/`, `config/`, `widget/`, `cdc/`, `safety_input/`, `safety_output/`, `policy/`, `cache/`) — placeholders except `api/main.py` (see below).
- `api/main.py` — the only real application code so far. A FastAPI app with one endpoint, `GET /ready`, per DEC-117 (`specs/06-api-contracts.md` API-O-01). Uses Pydantic models (`ServiceHealth`, `ReadyResponse`), returns `ready: false` + all-false service flags, computed via `all(...)` so it can't desync from the individual flags. Does **not** eagerly connect to any backend — that's deliberate, see pitfalls below.
- `tests/architecture/import_graph.py` + `test_import_graph.py` — AST-based checker enforcing `specs/04-architecture.md` §5.1's forbidden module-to-module import table. 3 tests, all passing.
- `tests/api/test_ready.py` — 2 tests: one passes (schema shape is correct), one **fails on purpose** (`test_ready_reports_every_service_healthy` asserts the eventual `ready: true` target state, which can't be true yet since no real service exists). This is the whole point of Issue 03 — see pitfalls.
- `.github/workflows/ci.yml` — GitHub Actions: checkout → setup-python 3.14 → install deps → ruff → mypy → import-graph pytest → `/ready` smoke-test pytest. Triggers on every push/PR.
- `requirements.txt` (8 pins: fastapi, uvicorn, langgraph, httpx, qdrant-client, psycopg[binary], redis, PyYAML) + `requirements-llama-cpp.txt` (isolated, see pitfalls).
- `docker-compose.yml` — MVP skeleton, 12 services, schema-validated against a vendored `schemas/compose-spec.schema.json`, never run against a live Docker daemon (none available here).
- `pyproject.toml` — exists *only* for `[tool.pytest.ini_options] pythonpath = ["."]`. See pitfalls — do not remove this.
- `docs/agents/dev-environment.md` — **read this before assuming any environment capability**. It's the ground-truth probe result for Docker/GPU/CI/RunPod/compiler-toolchain in this exact execution environment. Keep it updated when the environment changes (it already got one stale-then-fixed cycle this session, see pitfalls).
- `README.md`, `LICENSE` (MIT, copyright `joeblack19996237`).
- Current CI status on `master`: **red, on purpose** (see pitfalls — do not "fix" this by weakening the test).

## Where we're stuck (not actually stuck — just correctly blocked)

Every remaining open item across all three issues needs something this execution environment cannot provide. None of these are things to solve by writing more code:

1. **`docker compose config`/`up` against a live daemon** — Docker isn't installed here (`docker: command not found`). Owner: DevOps, or anyone with Docker Desktop/Engine.
2. **vLLM installs and imports** — GPU-only, no CUDA host here (`nvidia-smi: command not found`). Owner: DevOps/AI on a CUDA-capable host (the RunPod dev rig, once TASK-003 stands it up).
3. **`llama-cpp-python` installs and imports** — needs a C/C++ build toolchain (cmake + MSVC/gcc), absent here. Not GPU-related — any machine with a compiler works.
4. **RunPod template + Network Volume boots, survives restart** — needs a live RunPod account/credentials this environment doesn't have.
5. **NFR-011 onboarding SLA** (new contributor reaches a working eval run in ≤2h) — a timed human trial, no agent can self-report this honestly.

If you're picking this repo up in an environment that *does* have Docker/GPU/a compiler/RunPod access, go close these items directly in the relevant issue file (each has an `Owner` and `Evidence to capture` already specified) — don't re-derive the requirements, they're already written.

## Next step

Phase 1's agent-closeable work is done. Two options, in likely priority order:

1. **If the manual-verify items above are now closeable** (you have Docker/GPU/RunPod/a compiler) — close them with real evidence in the issue files, following the same pattern already used throughout (quote the exact command + exact output, don't just check the box).
2. **Otherwise, move to Phase 2** — read `specs/10-build-plan.md` for the next TASK-### block after TASK-005 (the last one this session touched), and `specs/00-index.md` for orientation. Before drafting any new issue, run `/verifiable-acceptance-criteria` against it — every issue in Phase 1 needed at least one correction pass to keep its acceptance criteria actually checkable, and Phase 2 will introduce new infrastructure (real service wiring) that's likely to raise the same class of problem again.

Also worth doing early in the next session: re-run `docs/agents/dev-environment.md`'s probes if you suspect the environment changed (new tools installed, different sandbox) — don't trust the file blindly, it's a snapshot, not a live source.

## Pitfalls already hit — do not repeat these

1. **`pytest` vs `python -m pytest` have different `sys.path` behavior.** `python -m pytest` inserts the current directory onto `sys.path`; bare `pytest` does not. Every test in this session was run locally with `python -m pytest` and passed — then the exact same test failed in CI (which invokes bare `pytest`) with `ModuleNotFoundError: No module named 'api'`, not the intended assertion failure. Fixed via `pyproject.toml`'s `pythonpath = ["."]`. **If you add more top-level-package imports in tests, verify with bare `pytest` locally before trusting a `python -m pytest` pass — they are not equivalent.**

2. **Issue 03's failing test is failing ON PURPOSE.** `tests/api/test_ready.py::test_ready_reports_every_service_healthy` asserts `ready: true` and all services `true`. It fails right now because no real backend service exists yet — that's correct and expected until a later phase wires real health checks. **Do not "fix" this test to make CI green.** A green result here would mean the test stopped checking the real target state, not that the feature is more done than it is. CI on `master` will stay red because of this one test until real service health checks land — that's expected, not a broken pipeline.

3. **`GET /ready` must never eagerly connect to a backend service on startup.** If it did, the endpoint would hang/error in this environment (no Postgres/Qdrant/Redis running), and the check would silently stop being verifiable here. Keep it a pure computation over hardcoded/future-injected booleans.

4. **Python version: this repo targets 3.14, not 3.12.** `specs/13-decision-log.md` DEC-033 originally pinned 3.12; **DEC-134** (2026-07-11) re-pinned to 3.14 — **not because 3.12 was wrong**, but because this execution environment only has 3.14.3 installed and 7 of 8 core dependencies were verified compatible before the switch. If you're in a different environment with 3.12 available, this is worth revisiting, but don't assume 3.12 is still the target without checking `docs/agents/dev-environment.md` and DEC-134 first.

5. **`llama-cpp-python` and vLLM are deliberately NOT in `requirements.txt`.** They're isolated in `requirements-llama-cpp.txt` (llama-cpp-python) or not pinned in a requirements file at all (vLLM — GPU-only). Don't merge them back into the main file; doing so breaks the "zero conflicts" install check for everyone else, since these two can't even attempt install in most dev environments.

6. **TEI (text-embeddings-inference) has no dedicated PyPI client package.** `httpx` is pinned explicitly in `requirements.txt` to serve that role — this was originally missed (left as an implicit unpinned transitive dependency of `qdrant-client`) and only caught by code review. If you see "TEI client" referenced anywhere, it means `httpx`, not a separate SDK.

7. **`git push` always needs your explicit go-ahead in this session's working style** — it was never assumed, every push was confirmed first. Locally committing does not need confirmation; pushing does. Carry this convention forward unless told otherwise.

8. **Don't trust a spec citation without grepping `specs/13-decision-log.md` for the actual DEC.** Multiple times this session, a file's prose was stale relative to what the decision log said was current (LangGraph version, Python version, CI-connectivity status in `dev-environment.md` itself). The decision log is canonical; anything else that disagrees with it is the thing that's wrong, not the other way around.

9. **`.scratch/` is intentionally public/pushed** — the user considered gitignoring it (business-sensitive planning content) and explicitly decided against it. Don't re-litigate this without being asked.

10. **Before drafting or re-checking any issue's acceptance criteria, read `docs/agents/dev-environment.md` first.** It exists specifically so this doesn't have to be re-discovered by probing from scratch every session. If it's stale (environment changed), update it — don't just work around it silently.
