"""Shared Pydantic response schemas. `ErrorResponse` is the one error shape
every non-2xx response across this whole API surface uses (specs/06-api-contracts.md's
Error Schema) -- refusals are a separate, always-200 shape (DEC-042) and don't
use this.
"""

from __future__ import annotations

import uuid

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    details: dict[str, object] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Builds the one error shape every non-2xx response across this API
    uses, with a fresh `request_id` -- the single place every route/handler
    constructs one, rather than each repeating the same three-line shape."""
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=ErrorDetail(code=code, message=message, request_id=str(uuid.uuid4()))
        ).model_dump(),
    )
