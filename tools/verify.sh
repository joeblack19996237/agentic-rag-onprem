#!/usr/bin/env bash
# Local verification, matching .github/workflows/ci.yml: lint, type-check,
# then the full test suite except the API smoke test (tests/api/), which
# stays a separate, non-gating step below — it's deliberately red right now
# (Phase 1 has no backend services wired up, see tests/api/test_ready.py's
# own docstring). Folding it into the main gate would make this script fail
# every time regardless of what actually changed, defeating its purpose.
#
# Update this once Phase 2 wires real health checks and tests/api/ is
# expected to pass — fold it back into the main `pytest` run below instead
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

echo "==> full suite except the known-red API smoke test"
pytest --ignore=tests/api -q

echo "==> API smoke test (GET /ready) — expected red at this phase, not gated"
pytest tests/api -v || echo "    (red is expected here — see tests/api/test_ready.py's own docstring; this doesn't fail the script)"

echo "==> all gated checks passed"
