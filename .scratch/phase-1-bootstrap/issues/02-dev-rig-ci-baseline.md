Status: ready-for-agent

# Issue 02: Dev Rig Verification + CI Baseline

> Source: `specs/10-build-plan.md` TASK-003 (Dev Rig Verification, RunPod Template) + TASK-004 (CI Baseline), Phase 1. Traces to NFR-011, DEC-021, and `specs/09-deployment-ops.md`'s CI/CD Pipeline section.

## Parent

Depends on Issue 01 (`01-project-scaffold-dependencies.md`) — needs the scaffold and pinned dependencies to exist first.

## What to build

Verify the RunPod dev-rig template (with a persistent Network Volume for model cache) boots correctly and survives a pod restart without losing the model cache. In the same slice, stand up the CI baseline against the scaffold from Issue 01: a lint + type-check job, and the architecture import-graph check that enforces `04-architecture.md` §5.1's call-direction rules.

Both halves are TDD-Exempt (Infrastructure-as-Code) — correctness is verified by confirming the environment/pipeline behaves as documented, not by a failing test. The import-graph check runs against the empty scaffold and trivially passes at this stage (no cross-layer imports exist yet) — its value is that it now exists and will start catching violations the moment real code lands.

## Acceptance criteria

- [ ] RunPod template + Network Volume boots; model cache survives pod restart
- [ ] A new contributor following only the dev profile reaches a working eval run in ≤ 2 hours (NFR-011 acceptance target)
- [ ] CI pipeline is green on the scaffold commit
- [ ] Import-graph check step exists and runs in CI (even though it has nothing to catch yet)

## Blocked by

- Issue 01 (`01-project-scaffold-dependencies.md`)
