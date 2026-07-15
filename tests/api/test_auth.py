"""Auth middleware tests (TASK-033 Issue 01): JWT bearer (RS256/ES256/EdDSA
allowlist, DEC-061) + admin API key, against POST /v1/query as the first
protected route. JWKS keys are generated locally per test run, matching
DEC-062's air-gap static-bundle model -- no live IdP/JWKS endpoint involved.
`client`/`keys`/`admin_api_key` fixtures live in tests/api/conftest.py.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient


def _b64u(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def _forged_hs256_token_using_rsa_public_key(rsa_public_pem: bytes) -> str:
    """Hand-constructs an HS256 token signed with the RSA public key's PEM
    bytes as the HMAC secret -- the classic alg-confusion downgrade attack.
    Built by hand (not via jwt.encode) because PyJWT's own encode() refuses
    to use an asymmetric key as an HMAC secret, which would mask the actual
    thing under test here: does *decode* reject it given the accepted
    algorithms list never contains HS256.

    Carries a real, registered `kid` (`rsa-1`) -- **code-review finding,
    2026-07-15**: without one, this token (and the `alg: none` token below)
    was being rejected for an unrelated reason (`kid` missing, checked
    before the algorithm whitelist), which meant the test still passed even
    after deliberately re-adding HS256 to `ALLOWED_ALGORITHMS` -- exactly
    the regression it exists to catch. A resolvable `kid` makes the token
    reach the actual algorithm check."""

    header = _b64u(json.dumps({"alg": "HS256", "typ": "JWT", "kid": "rsa-1"}).encode())
    payload = _b64u(json.dumps({"sub": "attacker"}).encode())
    signing_input = header + b"." + payload
    signature = hmac.new(rsa_public_pem, signing_input, hashlib.sha256).digest()
    return (signing_input + b"." + _b64u(signature)).decode()


def _none_alg_token() -> str:
    """Same `kid`-must-resolve fix as the HS256 forgery above, same reason."""
    header = _b64u(json.dumps({"alg": "none", "typ": "JWT", "kid": "rsa-1"}).encode())
    payload = _b64u(json.dumps({"sub": "a"}).encode())
    return (header + b"." + payload + b".").decode()


def test_missing_credentials_returns_401(client: TestClient) -> None:
    response = client.post("/v1/query", json={"query": "hello"})
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthenticated"
    assert "request_id" in body["error"]


def test_rejects_hs256_and_none(client: TestClient, keys: dict[str, Any]) -> None:
    """Both forged tokens carry a resolvable `kid` (`rsa-1`) so they reach
    real verification rather than short-circuiting on a missing-`kid` error
    (mutation-tested, 2026-07-15 code review: without a resolvable `kid`
    this test still passed even after putting HS256 back in
    `ALLOWED_ALGORITHMS`, proving nothing). With a resolvable `kid`, this
    now proves the end-to-end outcome (a forged token is rejected) --
    mutation-testing *why* surfaced a second, independent layer specific to
    this system's design: the JWKS only ever holds asymmetric keys, so
    `signing_key.key` (an `RSAPublicKey` object) can't be used as an HMAC
    secret even if HS256 were mistakenly re-whitelisted (PyJWT raises a
    bare `TypeError` for that, still caught, still 401). That's a real,
    valuable second control, not a flaw in this test -- but it means this
    assertion alone doesn't cleanly isolate "the whitelist specifically" as
    the one thing standing between an attacker and acceptance; both layers
    are load-bearing together in this design."""
    rsa_public_pem = keys["rsa"].public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    forged_hs256 = _forged_hs256_token_using_rsa_public_key(rsa_public_pem)
    response = client.post(
        "/v1/query", json={"query": "hello"}, headers={"Authorization": f"Bearer {forged_hs256}"}
    )
    assert response.status_code == 401

    response = client.post(
        "/v1/query", json={"query": "hello"}, headers={"Authorization": f"Bearer {_none_alg_token()}"}
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("key_name", "algorithm", "kid"),
    [
        ("rsa", "RS256", "rsa-1"),
        ("ec", "ES256", "ec-1"),
        ("ed", "EdDSA", "ed-1"),
    ],
)
def test_accepts_whitelisted_alg(
    client: TestClient,
    keys: dict[str, Any],
    key_name: str,
    algorithm: str,
    kid: str,
) -> None:
    token = jwt.encode({"sub": "user-1"}, keys[key_name], algorithm=algorithm, headers={"kid": kid})
    response = client.post("/v1/query", json={"query": "hello"}, headers={"Authorization": f"Bearer {token}"})
    # A 501 (query stub, not yet implemented) proves auth accepted the
    # request and let it reach the route handler -- 401 would mean rejected.
    assert response.status_code == 501


@pytest.mark.parametrize(
    "make_token",
    [
        pytest.param(
            lambda keys: jwt.encode({"sub": "a"}, keys["rsa"], algorithm="RS256"),
            id="missing_kid",
        ),
        pytest.param(
            lambda keys: jwt.encode({"sub": "a"}, keys["rsa"], algorithm="RS256", headers={"kid": "not-in-jwks"}),
            id="unknown_kid",
        ),
        pytest.param(
            lambda keys: jwt.encode({"sub": "a"}, keys["rsa"], algorithm="RS256", headers={"kid": "ec-1"}),
            id="kid_type_mismatch",
        ),
    ],
)
def test_kid_edge_cases(
    client: TestClient,
    keys: dict[str, Any],
    make_token: Callable[[dict[str, Any]], str],
) -> None:
    token = make_token(keys)
    response = client.post("/v1/query", json={"query": "hello"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_admin_api_key_accepted(client: TestClient, admin_api_key: str) -> None:
    response = client.post("/v1/query", json={"query": "hello"}, headers={"X-Admin-Api-Key": admin_api_key})
    assert response.status_code == 501


def test_admin_api_key_rejected_when_wrong(client: TestClient) -> None:
    response = client.post(
        "/v1/query", json={"query": "hello"}, headers={"X-Admin-Api-Key": "wrong-key"}
    )
    assert response.status_code == 401


def test_ready_exempt_from_auth(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
