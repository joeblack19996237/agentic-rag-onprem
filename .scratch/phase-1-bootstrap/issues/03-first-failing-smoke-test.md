Status: ready-for-agent

# Issue 03: First Failing Smoke Test

> Source: `specs/10-build-plan.md` TASK-005 (First Failing Smoke Test), Phase 1 — this is the Phase 1 exit-gate task. Traces to REQ-011 and DEC-117 (`/ready` response schema, `specs/06-api-contracts.md`).

## Parent

Depends on Issue 01 (`01-project-scaffold-dependencies.md`) and Issue 02 (`02-dev-rig-ci-baseline.md`).

## What to build

Implement the minimal `api/` FastAPI app with a stub `GET /ready` endpoint, and write the first real test against it. This is the project's first genuine TDD red→green cycle, and completing it closes the Phase 1 exit gate.

The test asserts `GET /ready` returns the DEC-117 schema shape: `{ready: true, services: {...all true...}}`. Since no services are wired up yet, the correct implementation at this stage returns `ready: false` with every sub-service flag false. The test is expected to still fail here — but for the right reason (real, honest service state), which confirms the test harness itself is correctly wired before any real service health checks exist. Getting a "green" result here would actually indicate a broken test, not a working feature.

## Acceptance criteria

- [ ] `GET /ready` endpoint exists and returns the DEC-117 schema shape (even with all-false values)
      Verification: start the app locally and `curl -s http://localhost:8000/ready` (or the equivalent TestClient call) → JSON matches `{"ready": false, "services": {<all keys>: false}}`. Implementation note: the stub must not eagerly connect to Postgres/Qdrant/Redis on startup — if it does, this check silently stops being agent-groundable in an environment without those services running.
- [ ] Test run output shows the test failing against the stub for the expected reason (services not yet wired), not due to a broken test harness
      Verification: `pytest <test file path> -v` → test fails with an assertion mismatch on the `ready`/`services` values (the intended reason), not a collection error, import error, or unrelated exception

## Phase 1 exit gate (this issue closes it)

Agent-closable now: both Acceptance Criteria above.

The remaining exit-gate items require infrastructure or a human trial the current agent execution environment doesn't have — see Manual verification and Success metrics below.

## Manual verification (if any)

- [ ] [manual-verify] `docker compose up` reaches a container-healthy state for every service (even if not yet wired together)
      Owner: DevOps (needs Docker, plus a GPU-capable host for any GPU-backed service). Evidence to capture: `docker compose ps` output showing every service healthy. Docker is confirmed unavailable in the current agent execution environment.
- [ ] [manual-verify] CI runs and fails the deliberately-failing smoke test
      Owner: whoever connects this repo to a GitHub remote with Actions enabled (see Issue 02 — no remote, no `.github/workflows` yet). Evidence to capture: the CI run log showing the expected red result.

## Success metrics (not agent-verifiable; requires a live human trial)

- NFR-011 dev profile onboarding: a new contributor reaches this state in ≤ 2 hours. Same category as Issue 02's — a timed human-subject measurement, tracked separately, not a closing condition for the agent implementing this issue.

## Blocked by

- Issue 01 (`01-project-scaffold-dependencies.md`)
- Issue 02 (`02-dev-rig-ci-baseline.md`)
