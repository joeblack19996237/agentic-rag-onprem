"""Admin audit-list read store (TASK-033 Issue 04): backs
`GET /v1/admin/audit`, a filtered, cursor-paginated read over the real
`audit_events` table (`data-foundation` TASK-006). Read-only -- nothing in
this codebase writes `audit_events` rows yet (`TASK-024`, not built); this
module's own scope is proving the *read* side is correct against rows
seeded directly, the same way `document-ingest-pipeline`'s tests never
needed a live Postgres to prove `job_queue` read/write logic.

**Cursor pagination, deliberately independent of `admin/document_store.py`'s**
`_paginate`/`encode_cursor`/`decode_cursor` -- same opaque-base64-JSON shape
(`06-api-contracts.md`'s Pagination section applies repo-wide), keyset on
`(timestamp, audit_id)` DESC rather than `(created_at, document_id)`, but
not literally shared code. Per this issue's own risk-review: two fakes
(`FakeDocumentStore`, `FakeAuditEventStore`) isn't yet a pattern worth
abstracting into one generic pagination helper -- a third paginated admin
list would be the trigger, not this issue.

**`from`/`to` are required** (`06-api-contracts.md`'s API-A-03 row has no
`?` on them, unlike `user_id?`/`cursor?`/`limit?`) -- enforced at the route
layer (`api/audit_routes.py`), not here; this store trusts its caller to
have already validated both are present and parseable.
"""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from audit.models import AuditEvent

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def encode_cursor(*, last_seen_timestamp: datetime, last_seen_id: uuid.UUID) -> str:
    payload = json.dumps(
        {"last_seen_timestamp": last_seen_timestamp.isoformat(), "last_seen_id": str(last_seen_id)}
    )
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Raises `ValueError` for any malformed cursor -- callers at the HTTP
    boundary must treat this as a client error (`400`), not a `500`."""
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")))
        return (
            datetime.fromisoformat(payload["last_seen_timestamp"]),
            uuid.UUID(payload["last_seen_id"]),
        )
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Malformed cursor: {cursor!r}") from exc


@dataclass(frozen=True)
class AuditEventPage:
    items: list[AuditEvent]
    next_cursor: str | None


def _paginate(rows: list[AuditEvent], limit: int) -> AuditEventPage:
    """Given `rows` already sorted `(timestamp, audit_id)` DESC and
    containing at most one more than a page's worth (the "peek" pattern),
    returns the trimmed page plus `next_cursor`. Shared by
    `SqlAlchemyAuditEventStore` and `FakeAuditEventStore` -- both are in
    this one file, so this is the *within-file* sharing this module's own
    docstring says is fine; the *cross-file* sharing with
    `admin/document_store.py`'s equivalent helper is what's deliberately
    not done (Standards-axis code review, 2026-07-16)."""
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    next_cursor = None
    if has_more and page_rows:
        last = page_rows[-1]
        next_cursor = encode_cursor(last_seen_timestamp=last.timestamp, last_seen_id=last.audit_id)
    return AuditEventPage(items=page_rows, next_cursor=next_cursor)


class AuditEventStore(Protocol):
    def list_events(
        self, *, from_ts: datetime, to_ts: datetime, user_id: str | None, cursor: str | None, limit: int
    ) -> AuditEventPage: ...


class SqlAlchemyAuditEventStore:
    """Real implementation, reading `audit_events` directly. Core-style
    `select()` executed via `session.execute(...)`, matching
    `admin/document_store.py`'s `SqlAlchemyDocumentStore` pattern -- the
    compiled statement a caller issues is directly assertable against a
    mocked `Session` (Tier A per the issue's risk-review)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_events(
        self, *, from_ts: datetime, to_ts: datetime, user_id: str | None, cursor: str | None, limit: int
    ) -> AuditEventPage:
        stmt = select(AuditEvent).where(AuditEvent.timestamp >= from_ts, AuditEvent.timestamp <= to_ts)
        if user_id is not None:
            stmt = stmt.where(AuditEvent.user_id == user_id)
        stmt = stmt.order_by(AuditEvent.timestamp.desc(), AuditEvent.audit_id.desc())
        if cursor is not None:
            last_seen_timestamp, last_seen_id = decode_cursor(cursor)
            stmt = stmt.where(
                tuple_(AuditEvent.timestamp, AuditEvent.audit_id) < (last_seen_timestamp, last_seen_id)
            )
        # Fetch one extra row as a "peek" -- if it comes back, there's a
        # next page; either way it's never included in the returned page.
        stmt = stmt.limit(limit + 1)
        rows = list(self._session.execute(stmt).scalars().all())
        return _paginate(rows, limit)


class FakeAuditEventStore:
    """In-memory fake for tests -- dict-backed, following this repo's
    established `Protocol` + fake pattern (`ingest/job_store.py`'s
    `InMemoryJobStore`). `seed()` lets a test populate rows directly, the
    same shape as `admin/document_store.py`'s `FakeDocumentStore.seed()`,
    since there is no write path to drive this through yet (`TASK-024`)."""

    def __init__(self) -> None:
        self._events: dict[uuid.UUID, AuditEvent] = {}

    def seed(self, event: AuditEvent) -> None:
        self._events[event.audit_id] = event

    def list_events(
        self, *, from_ts: datetime, to_ts: datetime, user_id: str | None, cursor: str | None, limit: int
    ) -> AuditEventPage:
        rows = [e for e in self._events.values() if from_ts <= e.timestamp <= to_ts]
        if user_id is not None:
            rows = [e for e in rows if e.user_id == user_id]
        rows.sort(key=lambda e: (e.timestamp, e.audit_id), reverse=True)
        if cursor is not None:
            last_seen_timestamp, last_seen_id = decode_cursor(cursor)
            rows = [e for e in rows if (e.timestamp, e.audit_id) < (last_seen_timestamp, last_seen_id)]

        return _paginate(rows, limit)
