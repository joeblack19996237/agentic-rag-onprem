"""Regenerate tests/api/openapi_snapshot.json from the live FastAPI app.

Promoted from an inline `python -c "..."` one-liner, hand-rolled once per
route-adding issue (TASK-033 Issue 02, then again Issue 03) without ever
being written down -- tools/README.md's own cross-session-recurrence trigger
(a pattern hand-rolled in two separate sessions, neither retyping it twice
*within* itself, so neither individually tripped the promotion signal).

Run this after adding/changing a route, then hand-verify the diff against
specs/06-api-contracts.md before committing -- this script only captures
the schema, it doesn't check it against the spec (tests/api/test_openapi_contract.py
does the ongoing drift check once a snapshot is committed).

Exit 0 on success. Exit 1 if the app fails to import or the schema can't be
written.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = REPO_ROOT / "tests" / "api" / "openapi_snapshot.json"


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from api.main import app
    except ImportError as exc:
        print(f"Failed to import api.main.app: {exc}", file=sys.stderr)
        return 1

    app.openapi_schema = None
    schema = app.openapi()
    SNAPSHOT_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {SNAPSHOT_PATH.relative_to(REPO_ROOT)}")
    print("Hand-verify the diff against specs/06-api-contracts.md before committing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
