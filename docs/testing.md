# Testing Guide

> How to write a test in this repo, what to avoid, and a live inventory of every test that actually exists (as of 2026-07-13, 3 test modules / 4 files). This is a *practice* doc — for the spec-level catalog of every test planned across all build phases (`TEST-001`..`TEST-040`), see `specs/11-test-plan.md` instead; this file only documents what's implemented today. Keep the inventory table below in sync whenever a test is added, removed, or changes what it covers — it's the whole point of this file.

## How to write a test here

The 3 test modules that exist today (see inventory below) all follow the same shape. Match it rather than inventing a new one:

1. **Check-style tests** (a rule you assert holds across the repo, not a single component's behavior) get an implementation module plus a test module, both under `tests/<domain>/` — e.g. `tests/architecture/import_graph.py` + `test_import_graph.py`, `tests/docs/doc_drift.py` + `test_doc_drift.py`. The implementation module exposes plain functions that return a list of human-readable violation strings (`[]` means clean). The test module imports it bare (`from doc_drift import ...`) — pytest's default import mode puts the test file's own directory on `sys.path` when there's no `__init__.py` there, so this resolves without packaging tricks. **Do not add `__init__.py` to `tests/<domain>/` directories** — it would break this.
2. **Component tests** (a single piece of real application code, like a FastAPI route) test it directly against its real module — no separate implementation module needed. `tests/api/test_ready.py` imports `api.main` directly (`from api.main import ServiceHealth, app`).
3. Every check-style test module includes one test that runs the check against the real repo (`REPO_ROOT = Path(__file__).resolve().parents[2]`) and asserts zero violations. This is the test that actually gates CI — the synthetic cases exist to prove the check works, not to replace this one.
4. Cover both directions for any check: a synthetic case that should stay clean (no false positives) and one that should trip it (no false negatives). See `test_doc_drift.py`'s `test_ignores_dec_ids_that_do_resolve` paired with `test_detects_a_dangling_dec_reference`.
5. Use pytest's `tmp_path` fixture for anything that needs its own throwaway directory tree. Never write scratch files into the real repo tree from a test.
6. Follow this project's TDD discipline (`.claude/skills/tdd/`): write the test first, run it, confirm it fails for the *right* reason (an assertion mismatch, not a collection/import error), then implement until it passes. `.scratch/phase-1-bootstrap/issues/03-first-failing-smoke-test.md` records a real worked example, including a red run that failed for the *wrong* reason (a `sys.path` bug) that had to be fixed before the red-for-the-right-reason state was reached.
7. Before calling a test "passing" or "done," actually run it (`pytest <file> -v`) and read the real output. A test you wrote but never executed isn't verified — see `CLAUDE.md`'s "Running and verifying this repo."

## What to avoid

- **Don't assume Docker, a GPU, or any live backend service is reachable.** This agent's execution environment has none of those (`docs/agents/dev-environment.md`). Follow `specs/13-decision-log.md` DEC-135's tiering: fake/stub the external client as the default (the `SafetyRailAdapter`/`ECMAdapter` Protocol-substitution pattern this spec already establishes), reach for a real live-service integration test only when one can actually be run here, and split anything that can't into an agent-checkable proxy plus a named `[manual-verify]` item.
- **Don't let a test pass only because of an accidentally-correct `sys.path`.** Both bare `pytest` and `python -m pytest` must resolve first-party imports identically. This repo hit a real CI failure from this once — `ModuleNotFoundError: No module named 'api'` in CI while the exact same test passed locally, because only `python -m pytest` had been run locally. `pyproject.toml`'s `pythonpath = ["."]` fixes this at the root — don't remove it, and don't paper over a future regression here with a per-file `sys.path.insert` workaround instead of fixing the root cause.
- **Don't "fix" a deliberately-red test by weakening its assertion.** `tests/api/test_ready.py::test_ready_reports_every_service_healthy` is red on purpose — Phase 1 has no backend services to check yet, so asserting `ready: true` would be dishonest. If a test is red because the underlying capability genuinely isn't built yet, leave it red with a comment explaining why (as that test already does) rather than loosening the assertion to make CI green.
- **Don't test private implementation details a caller can't observe.** Assert on the public surface — an HTTP response body, a function's returned violation list — not on private internal state. None of the 3 existing test modules reach into private attributes; keep it that way.
- **Don't trust a new check-style test until you've proven it catches the real bug it's for.** Before relying on a drift/lint-style check, reproduce the actual incident it's meant to prevent (in a `tmp_path` or a temp copy of the repo) and confirm the check flags it. `tests/docs/test_doc_drift.py` was verified this way against the real README-staleness bug this session hand-fixed earlier — not just against its own synthetic fixtures.
- **Don't leave a new or changed test uncommitted alongside the code it covers.** A test isn't real project memory — reusable by the next session or the next agent — until it's committed with the change it protects, per `CLAUDE.md`'s documentation-conventions rule.

## Current test inventory

| Module | Type | Covers | Run it |
|---|---|---|---|
| `tests/architecture/import_graph.py` + `test_import_graph.py` | Static/AST check | Forbidden module-to-module import edges per `specs/04-architecture.md` §5.1 (e.g. `retrieve/` may never import `generate/`, `acl/`, or `verify/`) | `pytest tests/architecture/test_import_graph.py -q` |
| `tests/api/test_ready.py` | Component (FastAPI `TestClient`) | `GET /ready`'s response shape (DEC-117) and its honest not-ready state — Phase 1 has no backend services wired, so `ready: false` is the only correct value right now | `pytest tests/api/test_ready.py -v` |
| `tests/docs/doc_drift.py` + `test_doc_drift.py` | Static/text check | `DEC-###` reference integrity (no dangling or duplicate ids across `specs/`, `docs/`, `.scratch/`, `CLAUDE.md`, `README.md`) and `README.md` ↔ `.scratch/*/issues/*.md` issue-status sync | `pytest tests/docs/test_doc_drift.py -v` |

All three run in CI on every push/PR (`.github/workflows/ci.yml`) and, except the intentionally-red `/ready` smoke test, as a local pre-commit gate too (`.pre-commit-config.yaml` — `pre-commit install` once per clone). Run everything locally with `pytest` from the repo root — see `CLAUDE.md`'s "Running and verifying this repo" for the full local-verification command list (`ruff check .`, `mypy .`, `pytest`).

## Planned but not yet implemented

`specs/11-test-plan.md` is the canonical, spec-level catalog of every test planned across Phase 2+ (`TEST-001`..`TEST-040`: unit, integration, contract, and E2E layers, each traced to a `REQ-###`/`NFR-###`). Its Test Environments table (amended by DEC-135) records which environment tier each planned test targets — check it before assuming a planned test can run in this agent's own sandbox. When a `TEST-###` gets implemented, add its module to the inventory table above; this file tracks what exists, `11-test-plan.md` tracks what's planned.
