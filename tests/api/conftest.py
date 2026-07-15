"""Shared fixtures for tests/api/. A real conftest.py, auto-discovered by
pytest's own fixture machinery -- never explicitly dotted-imported by any
test module here, which is what would recreate the collision
`tests/ingest/pdf_docx_fixtures.py`'s docstring warns about (pytest
auto-importing conftest.py as a bare top-level module while a dotted import
elsewhere loads the same file under a second module identity)."""

from __future__ import annotations

import json
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
