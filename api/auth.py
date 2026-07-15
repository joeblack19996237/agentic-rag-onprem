"""JWT bearer + admin API key authentication (TASK-033 Issue 01).

JWT: algorithm-whitelisted to RS256/ES256/EdDSA (DEC-061) -- HS256/HS384/HS512
and `none` are never in the accepted list, which is what actually blocks the
classic alg-confusion downgrade attack (empirically confirmed against this
repo's pinned PyJWT[crypto]==2.13.0, 2026-07-15: a token forged with HS256
using the server's own RSA public key as the HMAC secret is rejected purely
because HS256 is absent from `algorithms=[...]`, before key material is ever
inspected). JWKS is a small, static, pre-imported bundle (DEC-062, air-gap) --
a token's `kid` must be present and match a key in the bundle; there is no
"try every key" fallback, which would add complexity and attack surface for
no benefit against a bundle this size.

Admin API key: a flat, config-driven alternative to JWT on admin-scoped
routes (NFR-009), compared via `hmac.compare_digest` rather than `==` to
avoid a timing side-channel on the comparison.
"""

from __future__ import annotations

import hmac
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import jwt
from fastapi import Header, Request

ALLOWED_ALGORITHMS = ["RS256", "ES256", "EdDSA"]

AuthMethod = Literal["jwt", "admin_api_key"]


class AuthenticationError(Exception):
    """Raised for any authentication failure. `api/main.py` registers an
    exception handler that converts this into the standard 401 error-response
    shape -- callers of `require_auth` never need to catch this themselves."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class AuthContext:
    subject: str
    method: AuthMethod


def load_jwks_bundle(path: Path) -> jwt.PyJWKSet:
    return jwt.PyJWKSet.from_dict(json.loads(path.read_text(encoding="utf-8")))


def verify_jwt(token: str, jwks: jwt.PyJWKSet) -> dict[str, object]:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Malformed JWT") from exc

    kid = header.get("kid")
    if kid is None:
        raise AuthenticationError("JWT is missing the 'kid' header")

    signing_key = next((key for key in jwks.keys if key.key_id == kid), None)
    if signing_key is None:
        raise AuthenticationError(f"No JWKS key found for kid {kid!r}")

    try:
        return jwt.decode(token, signing_key.key, algorithms=ALLOWED_ALGORITHMS)
    except (jwt.PyJWTError, TypeError, ValueError) as exc:
        # TypeError/ValueError, not just PyJWTError: PyJWT raises a bare
        # TypeError (not one of its own PyJWTError subclasses) when a
        # token's claimed algorithm doesn't match the key type resolved via
        # `kid` -- confirmed empirically, 2026-07-15. Catching only
        # PyJWTError here would let that case leak through as an uncaught
        # 500 instead of a 401.
        raise AuthenticationError("JWT signature verification failed") from exc


def verify_admin_api_key(provided: str, expected: str) -> bool:
    return hmac.compare_digest(provided, expected)


async def require_auth(
    request: Request,
    authorization: str | None = Header(default=None),
    x_admin_api_key: str | None = Header(default=None, alias="X-Admin-Api-Key"),
) -> AuthContext:
    if x_admin_api_key is not None:
        expected_key: str | None = getattr(request.app.state, "admin_api_key", None)
        if expected_key and verify_admin_api_key(x_admin_api_key, expected_key):
            return AuthContext(subject="admin-api-key", method="admin_api_key")
        raise AuthenticationError("Invalid admin API key")

    if authorization is not None:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthenticationError("Malformed Authorization header")
        jwks: jwt.PyJWKSet | None = getattr(request.app.state, "jwks", None)
        if jwks is None:
            raise AuthenticationError("No JWKS bundle configured")
        claims = verify_jwt(token, jwks)
        return AuthContext(subject=str(claims.get("sub", "")), method="jwt")

    raise AuthenticationError("Missing credentials")
