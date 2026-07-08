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
- [ ] Test run output shows the test failing against the stub for the expected reason (services not yet wired), not due to a broken test harness

## Phase 1 exit gate (this issue closes it)

- [ ] `docker compose up` reaches a container-healthy state for every service (even if not yet wired together)
- [ ] CI runs and fails the deliberately-failing smoke test
- [ ] A new contributor following only the `NFR-011` dev profile reaches this state in ≤ 2 hours

## Blocked by

- Issue 01 (`01-project-scaffold-dependencies.md`)
- Issue 02 (`02-dev-rig-ci-baseline.md`)
