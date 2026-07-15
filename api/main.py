"""FastAPI app. `GET /ready` is the Phase 1 scaffold (TASK-005); auth
(`api/auth.py`) and `POST /v1/query` (stubbed until Phase 3) land in
TASK-033 Issue 01. Every other route lands in later Issues as the
corresponding module is wired up.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.auth import AuthContext, AuthenticationError, load_jwks_bundle, require_auth
from api.ingest_routes import router as ingest_router
from api.schemas import ErrorResponse, error_response

app = FastAPI()
app.include_router(ingest_router)

# Static, pre-imported JWKS bundle (DEC-062, air-gap) -- no live JWKS
# endpoint fetch. Unset in an environment with no bundle configured, which
# fails every JWT auth attempt closed (require_auth raises AuthenticationError
# rather than treating "no bundle" as "skip verification").
_jwks_path = os.environ.get("JWKS_BUNDLE_PATH")
app.state.jwks = load_jwks_bundle(Path(_jwks_path)) if _jwks_path else None
app.state.admin_api_key = os.environ.get("ADMIN_API_KEY")


@app.exception_handler(AuthenticationError)
async def handle_authentication_error(request: Request, exc: AuthenticationError) -> JSONResponse:
    return error_response(401, "unauthenticated", exc.message)


@app.post(
    "/v1/query",
    status_code=501,
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        501: {"model": ErrorResponse, "description": "Not implemented until Phase 3"},
    },
)
async def post_query(auth: AuthContext = Depends(require_auth)) -> JSONResponse:
    """Registered and auth-enforced; returns 501 until Phase 3 wires the
    real query graph (specs/10-build-plan.md TASK-033's own text: "returns
    501 until Phase 3 lands" -- deliberate and temporary, not an unresolved
    placeholder). `06-api-contracts.md`'s Error Schema table doesn't list
    501 among its documented codes -- flagged as an update-specs candidate,
    not something to hand-fix here -- so this still returns the same
    structured error shape every other non-2xx response uses, rather than a
    bare, bodyless 501."""
    return error_response(501, "not_implemented", "Query generation is not implemented until Phase 3.")


class ServiceHealth(BaseModel):
    """DEC-117 full-dependency health check, per specs/06-api-contracts.md's
    API-O-01 contract. No real health checks exist yet (Phase 1) — every
    field defaults to False rather than being silently omitted, so /ready's
    shape is already correct even though its values aren't wired to
    anything real yet."""

    vllm: bool = False
    tei_embed: bool = False
    tei_rerank: bool = False
    nli: bool = False
    safety_input: bool = False
    safety_output: bool = False
    policy: bool = False
    qdrant: bool = False
    postgres: bool = False
    redis: bool = False


class ReadyResponse(BaseModel):
    ready: bool
    services: ServiceHealth


@app.get("/ready", response_model=ReadyResponse)
def get_ready() -> ReadyResponse:
    """Report aggregate readiness. Always returns 200 (per API-O-01) — a
    health-check endpoint returning 5xx during startup would be
    indistinguishable from "the endpoint itself is broken"."""
    services = ServiceHealth()
    return ReadyResponse(ready=all(services.model_dump().values()), services=services)
