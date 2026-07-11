"""Minimal FastAPI app — Phase 1 scaffold (TASK-005).

Only the GET /ready endpoint exists so far; every other route lands in
later phases as the corresponding module is wired up.
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


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
