"""Shared pytest fixtures across every tests/<domain>/ package -- auth
setup (`client`/`keys`/`admin_api_key`/`jwt_headers`) needed by both
tests/api/ and tests/admin/ (TASK-033 Issue 03), moved up from
tests/api/conftest.py once a second consumer needed the identical setup
rather than duplicating it (code review, Issue 02, 2026-07-15, flagged the
single-consumer copy of this same shape as Duplicated Code).

Deliberately **not** named `conftest.py` and **not** placed directly at
`tests/` -- pytest itself would happily auto-discover a root `tests/conftest.py`
alongside `tests/api/conftest.py`, but neither `tests/` nor `tests/api/` (nor
`tests/admin/`) carries an `__init__.py` (`docs/testing.md`'s own rule, so
check-style tests' bare `from doc_drift import ...` imports keep working).
Without `__init__.py` anywhere, mypy's default (no `--namespace-packages`)
file-to-module mapping names every rootless file by bare basename alone --
two files both literally named `conftest.py` anywhere under `tests/` collide
as the same module name ("Duplicate module named conftest"), confirmed
empirically, 2026-07-16, when a root `tests/conftest.py` was tried first.
Widening mypy's resolution mode (`--namespace-packages`/`--explicit-package-bases`)
would fix that collision too, but changes how *every* existing bare-imported
check-style test module resolves repo-wide -- too broad a blast radius for
this fixture-sharing refactor alone. A plain, non-magic filename sidesteps
the collision instead (the same fix `tests/ingest/pdf_docx_fixtures.py`'s
docstring already used for a related, but not identical, collision), imported
explicitly by both `tests/api/conftest.py` and `tests/admin/conftest.py`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm, OKPAlgorithm, RSAAlgorithm

from api.main import app


@pytest.fixture
def admin_api_key() -> str:
    return "test-admin-key-do-not-use-in-prod"  # noqa: S105 -- test fixture value, not a real secret


@pytest.fixture(scope="module")
def keys() -> dict[str, Any]:
    return {
        "rsa": rsa.generate_private_key(public_exponent=65537, key_size=2048),
        "ec": ec.generate_private_key(ec.SECP256R1()),
        "ed": ed25519.Ed25519PrivateKey.generate(),
    }


@pytest.fixture
def client(keys: dict[str, Any], admin_api_key: str) -> TestClient:
    bundle = {
        "keys": [
            json.loads(RSAAlgorithm.to_jwk(keys["rsa"].public_key())) | {"kid": "rsa-1", "use": "sig"},
            json.loads(ECAlgorithm.to_jwk(keys["ec"].public_key())) | {"kid": "ec-1", "use": "sig"},
            json.loads(OKPAlgorithm.to_jwk(keys["ed"].public_key())) | {"kid": "ed-1", "use": "sig"},
        ]
    }
    app.state.jwks = jwt.PyJWKSet.from_dict(bundle)
    app.state.admin_api_key = admin_api_key
    return TestClient(app)


@pytest.fixture
def jwt_headers(keys: dict[str, Any]) -> Callable[[], dict[str, str]]:
    """A quick "just give me a valid, accepted credential" builder for tests
    that don't care about JWT algorithm/kid specifics (those live in
    test_auth.py) and just need a route to authenticate successfully."""

    def _build() -> dict[str, str]:
        token = jwt.encode({"sub": "user-1"}, keys["rsa"], algorithm="RS256", headers={"kid": "rsa-1"})
        return {"Authorization": f"Bearer {token}"}

    return _build
