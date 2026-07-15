#!/usr/bin/env bash
# Local verification, matching .github/workflows/ci.yml: lint, type-check,
# then the full test suite except one specific test node
# (test_ready_reports_every_service_healthy), which stays a separate,
# non-gating step below — it's deliberately red right now (Phase 1 has no
# backend services wired up, see tests/api/test_ready.py's own docstring).
# Folding it into the main gate would make this script fail every time
# regardless of what actually changed, defeating its purpose.
#
# Fixed 2026-07-15 (TASK-033 Issue 01): this used to --ignore=tests/api
# entirely, which silently stopped gating everything else added to that
# directory once it grew past the one red test (test_auth.py,
# test_openapi_contract.py, test_query_stub.py were all running only in the
# "expected red, not gated" step below and were never actually enforced).
# Deselect only the one known-red node instead of excluding the whole
# directory, so anything new added there is gated by default.
#
# Update the deselect below once Phase 2 wires real health checks and that
# node is expected to pass — fold it back into the main `pytest` run instead
# of leaving this exception stale.
#
# Usage: tools/verify.sh
# Exit code: 0 if every gated step passed, 1 on the first failing one
# (output from that step is the last thing printed).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> ruff check ."
ruff check .

echo "==> mypy ."
mypy .

echo "==> full suite except the known-red /ready target-state test"
pytest -q --deselect tests/api/test_ready.py::test_ready_reports_every_service_healthy

echo "==> /ready target-state test (GET /ready reports all services healthy) — expected red at this phase, not gated"
pytest tests/api/test_ready.py::test_ready_reports_every_service_healthy -v || echo "    (red is expected here — see its own docstring; this doesn't fail the script)"

echo "==> all gated checks passed"
