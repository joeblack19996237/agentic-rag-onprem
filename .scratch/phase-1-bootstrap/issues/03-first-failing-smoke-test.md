Status: ready-for-human

<!-- 2026-07-11: all 3 agent-checkable acceptance criteria are done and verified, including a real CI-invocation bug (bare `pytest` vs `python -m pytest` sys.path difference) found and fixed along the way. Phase 1's agent-closable exit-gate work is complete. Only the docker-compose-healthy [manual-verify] item and the NFR-011 Success metric remain — neither closeable without Docker / a timed human trial. -->

# Issue 03: First Failing Smoke Test

> Source: `specs/10-build-plan.md` TASK-005 (First Failing Smoke Test), Phase 1 — this is the Phase 1 exit-gate task. Traces to REQ-011 and DEC-117 (`/ready` response schema, `specs/06-api-contracts.md`).
>
> **Correction (2026-07-11, `verifiable-acceptance-criteria` re-check)**: the "CI runs and fails the deliberately-failing smoke test" item below was drafted as `[manual-verify]` when this repo had no remote and no CI connection. That ground truth has since changed — Issue 02 closed with a real GitHub remote connected, Actions enabled, and a confirmed-live run (`docs/agents/dev-environment.md`'s CI/CD access section, updated same day). Per this skill's own worked-example precedent ("CI pipeline is green... if confirmed: grounded, Verification = `gh run list`"), this item is promoted out of Manual verification into Acceptance criteria. One caveat carried into its Verification line: actually triggering the check requires pushing the commit, and pushing is a user-confirmed action in this session (a standing convention, not a tool/credential gap) — so "grounded" here means the *querying* half is fully agent-drivable, not that the agent may push without asking first.

## Parent

Depends on Issue 01 (`01-project-scaffold-dependencies.md`) and Issue 02 (`02-dev-rig-ci-baseline.md`).

## What to build

Implement the minimal `api/` FastAPI app with a stub `GET /ready` endpoint, and write the first real test against it. This is the project's first genuine TDD red→green cycle, and completing it closes the Phase 1 exit gate.

The test asserts `GET /ready` returns the DEC-117 schema shape: `{ready: true, services: {...all true...}}`. Since no services are wired up yet, the correct implementation at this stage returns `ready: false` with every sub-service flag false. The test is expected to still fail here — but for the right reason (real, honest service state), which confirms the test harness itself is correctly wired before any real service health checks exist. Getting a "green" result here would actually indicate a broken test, not a working feature.

## Acceptance criteria

- [x] `GET /ready` endpoint exists and returns the DEC-117 schema shape (even with all-false values)
      Verification: start the app locally and `curl -s http://localhost:8000/ready` (or the equivalent TestClient call) → JSON matches `{"ready": false, "services": {<all keys>: false}}`. Implementation note: the stub must not eagerly connect to Postgres/Qdrant/Redis on startup — if it does, this check silently stops being agent-groundable in an environment without those services running.
      **Done (2026-07-11)**: `api/main.py` — `GET /ready` returns `{"ready": false, "services": {vllm/tei_embed/tei_rerank/nli/safety_input/safety_output/policy/qdrant/postgres/redis: false}}`, computed via `all(services.model_dump().values())` rather than hardcoded, so it stays correct once real checks replace the placeholders. No eager service connections — confirmed via `tests/api/test_ready.py::test_ready_returns_dec117_schema_shape`, which passes using `TestClient` alone (no live server, no backend services). **Correction (code-review finding)**: initial version used a bare `dict` return type; `specs/04-architecture.md`'s tech-stack table explicitly says "Type hints + Pydantic everywhere" for this project, so a plain dict on the very first endpoint would've set the wrong precedent. Refactored to `ServiceHealth`/`ReadyResponse` Pydantic models with `response_model=ReadyResponse`; also renamed the handler `ready()` → `get_ready()` (verb-noun, per the same standard). Re-verified: tests and lint still pass identically.
- [x] Test run output shows the test failing against the stub for the expected reason (services not yet wired), not due to a broken test harness
      Verification: `pytest <test file path> -v` → test fails with an assertion mismatch on the `ready`/`services` values (the intended reason), not a collection error, import error, or unrelated exception
      **Done (2026-07-11)**: `pytest tests/api/test_ready.py -v` → `test_ready_returns_dec117_schema_shape` PASSED, `test_ready_reports_every_service_healthy` FAILED with `assert False is True` (clean `AssertionError` on the `ready` value, not a collection/import error). Full suite (`pytest`, both this and Issue 02's architecture tests): 4 passed, 1 failed — the 1 failure is this intentional one.
- [x] CI runs the same test and shows it failing for the same reason (not just locally)
      Verification: push the commit implementing the `/ready` stub + its failing test (**requires explicit user confirmation before the push itself** — the querying half below is agent-drivable, the push is not assumed); then `gh run list --branch master --limit 1` → conclusion: `failure`; `gh run view <run-id> --log | grep -A10 "<test name>"` → the same assertion mismatch as the local run, not a collection/import error. Note this is a genuine *red* CI run by design (see "What to build" above) — a green run here would mean the test itself is broken, not that the feature is more done than intended.
      **First push attempt (2026-07-11) surfaced a real bug, not the intended result**: `gh run view 29148049637` → conclusion `failure`, but the failing step's log showed `ModuleNotFoundError: No module named 'api'` — a collection error, not the assertion mismatch this AC requires. Root cause: locally this had only been run via `python -m pytest` (which inserts repo root onto `sys.path`), but `.github/workflows/ci.yml` invokes bare `pytest`, which doesn't — so `from api.main import ...` couldn't resolve in CI even though it worked every time locally. Reproduced locally with bare `pytest` to confirm before fixing. **Fixed**: added `pyproject.toml` with `[tool.pytest.ini_options] pythonpath = ["."]`, which puts repo root on `sys.path` regardless of invocation style.
      **Done (2026-07-11, after the fix was pushed)**: `gh run view 29148153178` → conclusion `failure`; `lint-typecheck` job shows every step passing (checkout, setup-python, install deps, ruff, mypy, import-graph check) except "Smoke test (GET /ready) — expected red at this phase", which fails with `FAILED tests/api/test_ready.py::test_ready_reports_every_service_healthy - assert False is True` — the exact same assertion mismatch as the local run, not a collection/import error. AC genuinely closed.

## Phase 1 exit gate (this issue closes it)

Agent-closable now: all three Acceptance Criteria above (the CI one requires a user-confirmed push to actually trigger, per its Verification line).

The remaining exit-gate items require infrastructure or a human trial the current agent execution environment doesn't have — see Manual verification and Success metrics below.

## Manual verification (if any)

- [ ] [manual-verify] `docker compose up` reaches a container-healthy state for every service (even if not yet wired together)
      Owner: DevOps (needs Docker, plus a GPU-capable host for any GPU-backed service). Evidence to capture: `docker compose ps` output showing every service healthy. Docker is confirmed unavailable in the current agent execution environment.

## Success metrics (not agent-verifiable; requires a live human trial)

- NFR-011 dev profile onboarding: a new contributor reaches this state in ≤ 2 hours. Same category as Issue 02's — a timed human-subject measurement, tracked separately, not a closing condition for the agent implementing this issue.

## Blocked by

- Issue 01 (`01-project-scaffold-dependencies.md`)
- Issue 02 (`02-dev-rig-ci-baseline.md`)
