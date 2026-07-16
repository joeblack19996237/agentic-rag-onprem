"""`GET`/`PUT /v1/admin/documents` (TASK-033 Issue 03) -- cursor-paginated
document list and soft-delete/ACL-edit/authority_state update, backed by
`admin/document_store.py`.

**400, not 422, for request-body validation** -- same convention Issues 01/02
established (`api/ingest_routes.py`'s `acl_override` handling): `PUT`'s body
is accepted as a bare `dict[str, object]` and validated manually via
`DocumentUpdateRequest.model_validate(...)`, so a bad `lifecycle_state`
value, a bad `authority_state` value, or an empty `{}` body all fail through
one `except ValidationError` path into this API's own structured error
shape rather than FastAPI's default Pydantic-body 422.
`06-api-contracts.md`'s Error Schema table never lists 422 for any endpoint.

**`limit` is clamped, not rejected** -- `06-api-contracts.md`'s API-A-01 row
states "default 50, max 200" as a bound, and the issue's own risk-review
notes (`.scratch/api-surface/issues/03-admin-document-management.md`)
enumerate every case that must `400` (bad enum values, empty body) without
mentioning an out-of-range `limit`; clamping silently satisfies the stated
bound without inventing a new error case the issue never asked for. A
malformed `cursor`, by contrast, *is* rejected with `400` -- it's
untrusted, attacker-controllable input reaching a UUID/timestamp parse
(`docs/coding-standards.md`'s "validate at system boundaries" rule), not a
bound the spec already describes as a simple clamp.

**Known gap**: same admin-scope-auth gap as `api/ingest_routes.py`'s module
docstring (`api/auth.py` has no JWT scope concept yet) -- not re-explained
here.
"""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ValidationError, model_validator
from sqlalchemy.orm import Session

from admin.document_store import (
    MAX_LIMIT,
    AclUpdate,
    DocumentAcl,
    DocumentNotFoundError,
    DocumentStore,
    DocumentSummary,
    DocumentUpdate,
    SqlAlchemyDocumentStore,
    decode_cursor,
)
from api.auth import AuthContext, require_auth
from api.ingest_routes import get_session
from api.schemas import ErrorResponse, error_response

router = APIRouter()


class AclResponse(BaseModel):
    allow_principals: list[str]
    deny_principals: list[str]
    security_label: str
    retention_state: str


class DocumentResponse(BaseModel):
    document_id: str
    repository_id: str
    lifecycle_state: str
    authority_state: str | None
    created_at: str
    updated_at: str
    acl: AclResponse | None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    next_cursor: str | None


class AclUpdateRequest(BaseModel):
    allow_principals: list[str] | None = None
    deny_principals: list[str] | None = None
    security_label: str | None = None
    retention_state: str | None = None


class DocumentUpdateRequest(BaseModel):
    """`lifecycle_state`/`authority_state` are typed as closed `Literal`s so
    an unsupported value fails Pydantic validation the same way a missing
    field does -- both funnel through this module's one
    `except ValidationError` -> `400` path (see module docstring)."""

    acl: AclUpdateRequest | None = None
    lifecycle_state: Literal["deleted"] | None = None
    authority_state: Literal["authoritative", "draft", "deprecated"] | None = None

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> DocumentUpdateRequest:
        if self.acl is None and self.lifecycle_state is None and self.authority_state is None:
            raise ValueError("At least one of acl, lifecycle_state, authority_state is required")
        return self


def get_document_store(session: Session = Depends(get_session)) -> DocumentStore:
    return SqlAlchemyDocumentStore(session)


def _acl_to_response(acl: DocumentAcl | None) -> AclResponse | None:
    if acl is None:
        return None
    return AclResponse(
        allow_principals=acl.allow_principals,
        deny_principals=acl.deny_principals,
        security_label=acl.security_label,
        retention_state=acl.retention_state,
    )


def _summary_to_response(summary: DocumentSummary) -> DocumentResponse:
    return DocumentResponse(
        document_id=str(summary.document_id),
        repository_id=summary.repository_id,
        lifecycle_state=summary.lifecycle_state,
        authority_state=summary.authority_state,
        created_at=summary.created_at.isoformat(),
        updated_at=summary.updated_at.isoformat(),
        acl=_acl_to_response(summary.acl),
    )


@router.get(
    "/v1/admin/documents",
    response_model=DocumentListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Malformed cursor"},
        401: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
    },
)
async def list_documents(
    cursor: str | None = None,
    limit: int = 50,
    auth: AuthContext = Depends(require_auth),
    store: DocumentStore = Depends(get_document_store),
) -> DocumentListResponse | object:
    limit = max(1, min(limit, MAX_LIMIT))
    if cursor is not None:
        try:
            decode_cursor(cursor)
        except ValueError as exc:
            return error_response(400, "invalid_request", f"Invalid cursor: {exc}")

    page = store.list_documents(cursor=cursor, limit=limit)
    return DocumentListResponse(
        items=[_summary_to_response(item) for item in page.items], next_cursor=page.next_cursor
    )


@router.put(
    "/v1/admin/documents/{document_id}",
    response_model=DocumentResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or empty update body"},
        401: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        404: {"model": ErrorResponse, "description": "Unknown document_id"},
    },
)
async def put_document(
    document_id: uuid.UUID,
    body: dict[str, object],
    auth: AuthContext = Depends(require_auth),
    store: DocumentStore = Depends(get_document_store),
) -> DocumentResponse | object:
    try:
        parsed = DocumentUpdateRequest.model_validate(body)
    except ValidationError as exc:
        return error_response(400, "invalid_request", f"Invalid request body: {exc}")

    acl_update = None
    if parsed.acl is not None:
        acl_update = AclUpdate(
            allow_principals=parsed.acl.allow_principals,
            deny_principals=parsed.acl.deny_principals,
            security_label=parsed.acl.security_label,
            retention_state=parsed.acl.retention_state,
        )
    update = DocumentUpdate(
        acl=acl_update, lifecycle_state=parsed.lifecycle_state, authority_state=parsed.authority_state
    )

    try:
        summary = store.update_document(document_id, update)
    except DocumentNotFoundError:
        return error_response(404, "not_found", f"No document {document_id}")

    return _summary_to_response(summary)
