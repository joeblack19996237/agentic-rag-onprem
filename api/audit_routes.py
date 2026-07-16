"""`GET /v1/admin/audit` (TASK-033 Issue 04) -- filtered, cursor-paginated
read over `audit_events`, backed by `audit/event_store.py`.

**`from`/`to` are required, validated manually -> `400`, not FastAPI's
automatic query-param `422`** -- same 400-not-422 convention Issues 01-03
established for request-body validation (`api/ingest_routes.py`'s
`acl_override`, `api/admin_routes.py`'s `PUT` body), extended here to a
query param because `06-api-contracts.md`'s API-A-03 row explicitly commits
to `400` (never `422`, across every endpoint in this API surface) and lists
`from`/`to` as required (no `?`, unlike `user_id?`/`cursor?`/`limit?`).
Accepted as bare strings (`Query(alias=...)`, not `datetime`-typed) so
FastAPI never gets the chance to auto-coerce-and-422 before this module's
own parsing runs.

**`limit` is clamped, not rejected** -- same call as `api/admin_routes.py`'s
own module docstring makes for the same reason: the issue's risk-review
enumerates every case that must `400` and out-of-range `limit` isn't one of
them.

**Known gap**: same admin-scope-auth gap as `api/ingest_routes.py`'s module
docstring (`api/auth.py` has no JWT scope concept yet, so the `403`
`06-api-contracts.md`'s API-A-03 row documents for an insufficiently-scoped
token is currently unreachable) -- not re-explained here.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.auth import AuthContext, require_auth
from api.ingest_routes import get_session
from api.schemas import ErrorResponse, error_response
from audit.event_store import MAX_LIMIT, AuditEventStore, SqlAlchemyAuditEventStore, decode_cursor
from audit.models import AuditEvent

router = APIRouter()


class AuditEventResponse(BaseModel):
    audit_id: str
    conversation_id: str
    user_id: str
    session_id: str
    query: str
    retrieved_chunk_ids: list[str]
    answer_text: str
    citations: list[dict[str, object]]
    retrieval_safety_verdicts: list[dict[str, object]] | None
    safety_input_verdict: dict[str, object] | None
    safety_output_verdict: dict[str, object] | None
    verification_result: dict[str, object]
    refusal_reason_actual: str | None
    refusal_reason_shown: str | None
    intent: str
    context_fingerprint: dict[str, object]
    revision_count: int
    policy_waiver_id: str | None
    intent_class: str | None
    nli_performed: bool | None
    latency_ms: int
    timestamp: str


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    next_cursor: str | None


def get_audit_event_store(session: Session = Depends(get_session)) -> AuditEventStore:
    return SqlAlchemyAuditEventStore(session)


def _parse_required_timestamp(value: str | None) -> datetime | None:
    """Returns `None` (a 400-worthy problem, not a value) for a missing or
    malformed timestamp -- the caller decides the exact error message."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _event_to_response(event: AuditEvent) -> AuditEventResponse:
    return AuditEventResponse(
        audit_id=str(event.audit_id),
        conversation_id=event.conversation_id,
        user_id=event.user_id,
        session_id=event.session_id,
        query=event.query,
        retrieved_chunk_ids=list(event.retrieved_chunk_ids),
        answer_text=event.answer_text,
        citations=event.citations,
        retrieval_safety_verdicts=event.retrieval_safety_verdicts,
        safety_input_verdict=event.safety_input_verdict,
        safety_output_verdict=event.safety_output_verdict,
        verification_result=event.verification_result,
        refusal_reason_actual=event.refusal_reason_actual,
        refusal_reason_shown=event.refusal_reason_shown,
        intent=event.intent,
        context_fingerprint=event.context_fingerprint,
        revision_count=event.revision_count,
        policy_waiver_id=str(event.policy_waiver_id) if event.policy_waiver_id else None,
        intent_class=event.intent_class,
        nli_performed=event.nli_performed,
        latency_ms=event.latency_ms,
        timestamp=event.timestamp.isoformat(),
    )


@router.get(
    "/v1/admin/audit",
    response_model=AuditEventListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Missing/malformed from, to, or cursor"},
        401: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
    },
)
async def list_audit_events(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    user_id: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    auth: AuthContext = Depends(require_auth),
    store: AuditEventStore = Depends(get_audit_event_store),
) -> AuditEventListResponse | object:
    from_ts = _parse_required_timestamp(from_)
    if from_ts is None:
        return error_response(400, "invalid_request", "'from' is required and must be an ISO-8601 timestamp")
    to_ts = _parse_required_timestamp(to)
    if to_ts is None:
        return error_response(400, "invalid_request", "'to' is required and must be an ISO-8601 timestamp")

    if cursor is not None:
        try:
            decode_cursor(cursor)
        except ValueError as exc:
            return error_response(400, "invalid_request", f"Invalid cursor: {exc}")

    limit = max(1, min(limit, MAX_LIMIT))
    page = store.list_events(from_ts=from_ts, to_ts=to_ts, user_id=user_id, cursor=cursor, limit=limit)
    return AuditEventListResponse(
        items=[_event_to_response(event) for event in page.items], next_cursor=page.next_cursor
    )
