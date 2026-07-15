"""OpenAPI schema-drift contract test (TASK-033 Issue 01). Generates the
schema from the FastAPI app in-process (no live server) and diffs it against
a committed snapshot -- catches undocumented drift after this point. The
snapshot's *initial* correspondence to specs/06-api-contracts.md's
documented shapes was hand-verified once, at authoring time (2026-07-15,
against §2 API-Q-01's `POST /v1/query` row and the Error Schema table); this
test does not and cannot mechanically re-verify spec-conformance on every
run, only that the schema hasn't silently changed since that hand-check.
"""

from __future__ import annotations

import json
from pathlib import Path

from api.main import app

SNAPSHOT_PATH = Path(__file__).parent / "openapi_snapshot.json"
_DRIFT_TEST_PATH = "/v1/__drift_test_only"


def _current_schema() -> dict[str, object]:
    # Bypass FastAPI's own schema cache so this always reflects the live
    # route table, not a stale cached copy from an earlier test module.
    app.openapi_schema = None
    return app.openapi()


def test_matches_committed_snapshot() -> None:
    current = _current_schema()
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert current == snapshot


def test_detects_undocumented_drift() -> None:
    """**Rewritten, code review 2026-07-15**: the original version deep-copied
    the snapshot, mutated the copy, and asserted the copy differed from the
    original -- true of any two non-identical dicts, so it never actually
    called `_current_schema()`/`app.openapi()` and proved nothing about
    whether *this test suite's real comparison mechanism* can catch a real
    schema change. This version genuinely registers an undocumented route on
    the live app, regenerates the schema for real, and confirms *that*
    diverges from the snapshot -- then removes the route so no state leaks
    into any other test module importing the same `app` singleton."""
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    async def _throwaway() -> dict[str, str]:
        return {}

    app.add_api_route(_DRIFT_TEST_PATH, _throwaway, methods=["GET"])
    try:
        drifted_schema = _current_schema()
        assert drifted_schema != snapshot
        assert _DRIFT_TEST_PATH in drifted_schema["paths"]  # type: ignore[operator]
    finally:
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != _DRIFT_TEST_PATH]
        app.openapi_schema = None
