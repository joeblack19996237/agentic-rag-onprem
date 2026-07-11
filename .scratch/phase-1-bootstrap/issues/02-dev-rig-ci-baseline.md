Status: ready-for-human

<!-- 2026-07-11: both agent-checkable acceptance criteria are done and verified (see checkmarks below). Only the 3 [manual-verify] items remain (RunPod boot/restart, live CI-green, import-graph-in-CI) plus the NFR-011 Success metric — none agent-closeable in this environment. -->

# Issue 02: Dev Rig Verification + CI Baseline

> Source: `specs/10-build-plan.md` TASK-003 (Dev Rig Verification, RunPod Template) + TASK-004 (CI Baseline), Phase 1. Traces to NFR-011, DEC-021, and `specs/09-deployment-ops.md`'s CI/CD Pipeline section.
>
> **Correction (2026-07-11, targeted `verifiable-acceptance-criteria` re-check)**: the import-graph-check acceptance criterion below previously said "run the check locally (the entry point this task creates)" without naming a concrete script path, tool, or invocation — a self-reference with nothing to point at yet, the same class of gap found and fixed in Issue 01's compose-schema AC. Rewritten to name a concrete file (`tests/architecture/test_import_graph.py`), its rule source (`04-architecture.md` §5.1's Forbidden column), and an exact command. A fresh independent re-check additionally flagged that §5.1's Forbidden column mixes true module-to-module import bans with non-import infra/service constraints (e.g. "never persist directly to Qdrant") — the rewrite scopes the check to the former only and says so explicitly, so two different implementers can't produce two different, silently-incompatible encodings of the same table. Not yet implemented, so corrected in place. The rest of this issue (CI-workflow-YAML AC, the three `[manual-verify]` items, the NFR-011 Success metrics split) was independently re-confirmed consistent with `docs/agents/dev-environment.md`'s ground truth and left untouched.

## Parent

Depends on Issue 01 (`01-project-scaffold-dependencies.md`) — needs the scaffold and pinned dependencies to exist first.

## What to build

Verify the RunPod dev-rig template (with a persistent Network Volume for model cache) boots correctly and survives a pod restart without losing the model cache. In the same slice, stand up the CI baseline against the scaffold from Issue 01: a lint + type-check job, and the architecture import-graph check that enforces `04-architecture.md` §5.1's call-direction rules.

Both halves are TDD-Exempt (Infrastructure-as-Code) — correctness is verified by confirming the environment/pipeline behaves as documented, not by a failing test. The import-graph check runs against the empty scaffold and trivially passes at this stage (no cross-layer imports exist yet) — its value is that it now exists and will start catching violations the moment real code lands.

## Acceptance criteria

- [x] Import-graph check exists at `tests/architecture/test_import_graph.py`, encodes `04-architecture.md` §5.1's forbidden **module-to-module** import edges as data (the subset of the Forbidden column naming another first-party module directory — e.g. `retrieve/` must never import `generate/`, `acl/`, or `verify/` — excludes the column's non-import constraints like "never persist directly to Qdrant," which are infra/service-access rules, not Python import edges, and are out of this script's scope), parses every first-party `.py` file's AST for `import`/`from` statements naming another module directory, and runs clean against the empty scaffold
      Verification: `pytest tests/architecture/test_import_graph.py -q` → exit 0, 0 failures (trivially — no cross-layer imports exist yet in the empty `__init__.py`-only scaffold)
      **Done (2026-07-11)**: checker logic lives in `tests/architecture/import_graph.py` (the §5.1 encoding + interpretive notes), `tests/architecture/test_import_graph.py` holds the pytest tests. `pytest tests/architecture/test_import_graph.py -q` → 3 passed: (1) zero violations against the real scaffold, (2) a self-test confirming the checker actually flags a deliberately-forbidden import in a temp fixture (not the real scaffold), (3) a data-sanity check that every module named in `FORBIDDEN_IMPORTS` is a real module. **Correction (code-review finding)**: `eval/` and `widget/` were initially left with an empty forbidden set, inconsistent with `rerank/`/`config/` — all four rows' "May call" column names zero first-party module targets (external service, or HTTP-only access to `api/`), so all four should get the same blanket-ban treatment. Fixed: `eval`/`widget` now also forbidden from importing any other first-party module, via a shared `_all_other_modules()` helper (also removes the `MODULES - {self}` duplication `rerank`/`config` had). Re-verified: 3/3 tests still pass.
- [x] CI workflow file(s) exist and are syntactically valid
      Verification: `python -c "import yaml; yaml.safe_load(open('<workflow file path>'))"` (or `actionlint` if available) → no parse errors
      **Done (2026-07-11)**: `.github/workflows/ci.yml` created (checkout, setup-python 3.14, install deps, ruff lint, mypy, the import-graph pytest check). `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` → no parse error.

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
