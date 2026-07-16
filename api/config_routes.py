"""`GET /v1/admin/config/models` (TASK-033 Issue 04) -- active
`model_versions` per role, backed by `config/active_model_version.py`'s
`list_active_model_versions`.

**Known gap**: same admin-scope-auth gap as `api/ingest_routes.py`'s module
docstring (`api/auth.py` has no JWT scope concept yet, so the `403`
`06-api-contracts.md`'s API-A-06 row documents for an insufficiently-scoped
token is currently unreachable) -- not re-explained here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.auth import AuthContext, require_auth
from api.ingest_routes import get_session
from api.schemas import ErrorResponse
from config.active_model_version import list_active_model_versions

router = APIRouter()


class RoleModelVersionResponse(BaseModel):
    role: str
    model_version: str | None


class ModelVersionListResponse(BaseModel):
    models: list[RoleModelVersionResponse]


@router.get(
    "/v1/admin/config/models",
    response_model=ModelVersionListResponse,
    responses={401: {"model": ErrorResponse, "description": "Missing or invalid credentials"}},
)
async def get_config_models(
    auth: AuthContext = Depends(require_auth), session: Session = Depends(get_session)
) -> ModelVersionListResponse:
    results = list_active_model_versions(session)
    return ModelVersionListResponse(
        models=[RoleModelVersionResponse(role=r.role, model_version=r.model_version) for r in results]
    )
