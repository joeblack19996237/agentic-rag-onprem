Status: ready-for-agent

# Issue 02: Dev Rig Verification + CI Baseline

> Source: `specs/10-build-plan.md` TASK-003 (Dev Rig Verification, RunPod Template) + TASK-004 (CI Baseline), Phase 1. Traces to NFR-011, DEC-021, and `specs/09-deployment-ops.md`'s CI/CD Pipeline section.

## Parent

Depends on Issue 01 (`01-project-scaffold-dependencies.md`) — needs the scaffold and pinned dependencies to exist first.

## What to build

Verify the RunPod dev-rig template (with a persistent Network Volume for model cache) boots correctly and survives a pod restart without losing the model cache. In the same slice, stand up the CI baseline against the scaffold from Issue 01: a lint + type-check job, and the architecture import-graph check that enforces `04-architecture.md` §5.1's call-direction rules.

Both halves are TDD-Exempt (Infrastructure-as-Code) — correctness is verified by confirming the environment/pipeline behaves as documented, not by a failing test. The import-graph check runs against the empty scaffold and trivially passes at this stage (no cross-layer imports exist yet) — its value is that it now exists and will start catching violations the moment real code lands.

## Acceptance criteria

- [ ] Import-graph check script exists and runs clean against the empty scaffold
      Verification: run the check locally (the entry point this task creates) → exit 0, no violations reported (none exist yet at this stage)
- [ ] CI workflow file(s) exist and are syntactically valid
      Verification: `python -c "import yaml; yaml.safe_load(open('<workflow file path>'))"` (or `actionlint` if available) → no parse errors

## Manual verification (if any)

- [ ] [manual-verify] RunPod template + Network Volume boots; model cache survives pod restart
      Owner: DevOps. Evidence to capture: pod boot log, plus a before/after cache-content check (file listing or checksum) across a restart. Requires a live RunPod account and credentials the current agent execution environment does not have.
- [ ] [manual-verify] CI pipeline is green on the scaffold commit
      Owner: whoever connects this repo to a GitHub remote with Actions enabled. Evidence to capture: `gh run list` output or the Actions tab. This repo currently has no git remote configured (`git remote -v` returns empty) and no `.github/workflows` directory — CI can't be observed as green by the agent until both exist.
- [ ] [manual-verify] Import-graph check step runs in CI (not just locally)
      Owner: same as above. Evidence to capture: the CI run log showing the step executed. Same blocker as above.

## Success metrics (not agent-verifiable; requires a live human trial)

- NFR-011 onboarding SLA: a new contributor following only the dev profile reaches a working eval run in ≤ 2 hours. This is a timed human-subject measurement, not a system behavior — no executing agent (including the one that built this) can self-verify it. Track separately, e.g. by timing an actual new contributor or external tester.

## Blocked by

- Issue 01 (`01-project-scaffold-dependencies.md`)
