"""Admin document list/update store (TASK-033 Issue 03): backs
`GET /v1/admin/documents` (cursor-paginated list) and
`PUT /v1/admin/documents/{document_id}` (soft-delete / ACL edit /
authority_state change) against `ingest/models.py`'s real
`documents`/`document_versions` schema.

**Cursor pagination**: opaque base64 JSON `{last_seen_timestamp, last_seen_id}`
over `(documents.created_at, documents.document_id)` DESC (`created_at`, not
`updated_at` -- an edit would otherwise move a row to a different page mid-browse;
`06-api-contracts.md`'s Pagination section, `.scratch/api-surface/issues/`
`03-admin-document-management.md`'s risk-review resolution). Keyset ("seek")
pagination, not offset -- stable under concurrent inserts by construction,
since each page's WHERE clause anchors on the last-seen row's own values
rather than a row count.

**"Current" ACL-bearing version**: the `document_versions` row where
`is_committed = True` and `superseded_by_version_id IS NULL` (DEC-071: "only
the latest committed version_id is queryable"; `superseded_by_version_id` is
set *on the old row* when a newer version replaces it, so the current row is
the one nothing points away from). A document with no such row yet (never
observed via this MVP's only writer, `api/ingest_routes.py`'s
`_create_document_and_version`, which always creates both rows together)
gets `acl=None` rather than being dropped from the list -- an admin should
still be able to see/soft-delete a document even if its ACL-bearing version
is somehow missing.

**Known gap** (same as `api/ingest_routes.py`'s module docstring): both
routes built on top of this store are documented as "admin scope" JWT, but
`api/auth.py` has no scope concept -- any correctly-signed JWT is accepted.
Not re-explained here; see that docstring for the full note.
"""

from __future__ import annotations

import base64
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Protocol, TypeVar

from sqlalchemy import select, tuple_
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from ingest.models import Document, DocumentVersion

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


class DocumentNotFoundError(LookupError):
    """Raised by `update_document` when `document_id` has no `documents` row.
    `api/admin_routes.py` maps this to `404 not_found` -- a normal, expected
    client-facing condition."""


class MissingAclVersionError(RuntimeError):
    """Raised by `update_document` when a `documents` row exists but has no
    current ACL-bearing `document_versions` row to apply an `acl` update to
    -- a server-side data-integrity invariant violation (see
    `update_document`'s own docstring), not a client-facing "not found".
    Deliberately *not* a `DocumentNotFoundError`/`LookupError` subclass, so
    it is not caught by the route's `except DocumentNotFoundError` and
    instead surfaces as an uncaught `500` -- a `404` here would wrongly
    claim the document itself doesn't exist (Standards-axis code review,
    2026-07-16)."""


@dataclass(frozen=True)
class DocumentAcl:
    allow_principals: list[str]
    deny_principals: list[str]
    security_label: str
    retention_state: str


@dataclass(frozen=True)
class DocumentSummary:
    document_id: uuid.UUID
    repository_id: str
    lifecycle_state: str
    authority_state: str | None
    created_at: datetime
    updated_at: datetime
    acl: DocumentAcl | None


@dataclass(frozen=True)
class DocumentPage:
    items: list[DocumentSummary]
    next_cursor: str | None


@dataclass(frozen=True)
class AclUpdate:
    allow_principals: list[str] | None = None
    deny_principals: list[str] | None = None
    security_label: str | None = None
    retention_state: str | None = None


@dataclass(frozen=True)
class DocumentUpdate:
    acl: AclUpdate | None = None
    lifecycle_state: str | None = None
    authority_state: str | None = None


# `audit/event_store.py` has a byte-for-byte identical copy of both
# encode_cursor/decode_cursor below -- deliberately not shared (this
# module's own docstring), but unlike `_paginate` (genuinely different
# column names/return types per store) these two have zero domain-specific
# variation, so a future format change (peer review, 2026-07-16) must be
# applied in both places or the two stores' cursors silently diverge.
def encode_cursor(*, last_seen_timestamp: datetime, last_seen_id: uuid.UUID) -> str:
    payload = json.dumps(
        {"last_seen_timestamp": last_seen_timestamp.isoformat(), "last_seen_id": str(last_seen_id)}
    )
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Raises `ValueError` for any malformed cursor -- callers at the HTTP
    boundary must treat this as a client error (`400`), not a `500`. Keep in
    sync with `audit/event_store.py`'s identical copy -- see the
    module-level comment above `encode_cursor`."""
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")))
        return (
            datetime.fromisoformat(payload["last_seen_timestamp"]),
            uuid.UUID(payload["last_seen_id"]),
        )
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Malformed cursor: {cursor!r}") from exc


class DocumentStore(Protocol):
    def list_documents(self, *, cursor: str | None, limit: int) -> DocumentPage: ...

    def get_document(self, document_id: uuid.UUID) -> DocumentSummary | None: ...

    def update_document(self, document_id: uuid.UUID, update: DocumentUpdate) -> DocumentSummary: ...


def _version_to_acl(version: DocumentVersion) -> DocumentAcl:
    return DocumentAcl(
        allow_principals=list(version.allow_principals),
        deny_principals=list(version.deny_principals),
        security_label=version.security_label,
        retention_state=version.retention_state,
    )


def _acl_update_values(current: DocumentAcl, changes: AclUpdate) -> tuple[dict[str, object], DocumentAcl]:
    """Splits an `AclUpdate` into (a) the `SET` values an `UPDATE
    document_versions` statement needs and (b) the resulting merged
    `DocumentAcl`, for a caller to persist and return respectively. Pure
    (no session access) so both `SqlAlchemyDocumentStore` and
    `FakeDocumentStore` share the same merge semantics rather than each
    reimplementing the four-field overlay independently."""
    values: dict[str, object] = {}
    if changes.allow_principals is not None:
        values["allow_principals"] = changes.allow_principals
    if changes.deny_principals is not None:
        values["deny_principals"] = changes.deny_principals
    if changes.security_label is not None:
        values["security_label"] = changes.security_label
    if changes.retention_state is not None:
        values["retention_state"] = changes.retention_state
    merged = DocumentAcl(
        allow_principals=changes.allow_principals
        if changes.allow_principals is not None
        else current.allow_principals,
        deny_principals=changes.deny_principals
        if changes.deny_principals is not None
        else current.deny_principals,
        security_label=changes.security_label
        if changes.security_label is not None
        else current.security_label,
        retention_state=changes.retention_state
        if changes.retention_state is not None
        else current.retention_state,
    )
    return values, merged


def _document_to_summary(document: Document, acl: DocumentAcl | None) -> DocumentSummary:
    return DocumentSummary(
        document_id=document.document_id,
        repository_id=document.repository_id,
        lifecycle_state=document.lifecycle_state,
        authority_state=document.authority_state,
        created_at=document.created_at,
        updated_at=document.updated_at,
        acl=acl,
    )


class _SortedByCreatedAtThenId(Protocol):
    """Read-only on purpose (`@property`, not a plain attribute) -- `Document`
    (mutable SQLAlchemy `Mapped` columns) and `DocumentSummary` (a frozen,
    read-only dataclass) both only need to satisfy *read* access to match
    this Protocol structurally; a plain mutable-attribute Protocol would
    reject the frozen dataclass side (mypy: "cannot be DocumentSummary")."""

    @property
    def created_at(self) -> datetime: ...
    @property
    def document_id(self) -> uuid.UUID: ...


_Row = TypeVar("_Row", bound=_SortedByCreatedAtThenId)


def _paginate(rows: Sequence[_Row], limit: int) -> tuple[list[_Row], str | None]:
    """Given `rows` already sorted `(created_at, document_id)` DESC and
    containing at most one more than a page's worth (the "peek" pattern --
    `SqlAlchemyDocumentStore` bounds this to `limit + 1` via SQL `LIMIT`,
    `FakeDocumentStore` passes its full filtered, unbounded list; both work
    here since only `len(rows) > limit` and a slice are needed), returns
    the trimmed page plus `next_cursor` (`None` on the last page). Shared
    by both stores so their pagination boundary can't drift out of sync
    (Standards-axis code review, 2026-07-16, on the pre-shared duplicate).
    `audit/event_store.py` has an analogous, deliberately *not* shared
    `_paginate` (different column names, different return type -- see that
    module's own docstring on why this one specifically isn't cross-file
    shared, unlike `encode_cursor`/`decode_cursor` above)."""
    has_more = len(rows) > limit
    page_rows = list(rows[:limit])
    next_cursor = None
    if has_more and page_rows:
        last = page_rows[-1]
        next_cursor = encode_cursor(last_seen_timestamp=last.created_at, last_seen_id=last.document_id)
    return page_rows, next_cursor


class SqlAlchemyDocumentStore:
    """Real implementation, reading/writing `documents` + `document_versions`
    directly. Core-style `select()`/`update()` statements executed via
    `session.execute(...)` throughout (matching
    `config/active_model_version.py`'s pattern) rather than ORM
    attribute-mutation + flush -- deliberately, so the compiled statement a
    caller issues is directly assertable against a mocked `Session` (Tier A
    per the issue's risk-review; a mock carries no real unit-of-work, so it
    can't observe an ORM flush's auto-generated UPDATE the same way)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_documents(self, *, cursor: str | None, limit: int) -> DocumentPage:
        stmt = select(Document).order_by(Document.created_at.desc(), Document.document_id.desc())
        if cursor is not None:
            last_seen_timestamp, last_seen_id = decode_cursor(cursor)
            stmt = stmt.where(
                tuple_(Document.created_at, Document.document_id) < (last_seen_timestamp, last_seen_id)
            )
        # Fetch one extra row as a "peek" -- if it comes back, there's a next
        # page; either way it's never included in the returned page itself.
        stmt = stmt.limit(limit + 1)
        rows = list(self._session.execute(stmt).scalars().all())

        page_rows, next_cursor = _paginate(rows, limit)
        acl_by_document_id = self._fetch_current_acl({row.document_id for row in page_rows})
        items = [_document_to_summary(row, acl_by_document_id.get(row.document_id)) for row in page_rows]
        return DocumentPage(items=items, next_cursor=next_cursor)

    def get_document(self, document_id: uuid.UUID) -> DocumentSummary | None:
        document = self._session.execute(
            select(Document).where(Document.document_id == document_id)
        ).scalar_one_or_none()
        if document is None:
            return None
        acl = self._fetch_current_acl({document_id}).get(document_id)
        return _document_to_summary(document, acl)

    def update_document(self, document_id: uuid.UUID, update: DocumentUpdate) -> DocumentSummary:
        """Issues at most one `UPDATE` per table touched: one covering
        every changed `documents` field (`lifecycle_state`/`authority_state`)
        and, separately, one covering every changed `document_versions`
        field (the `acl` payload) -- never split into more than one
        statement *per table*, matching the issue's "single UPDATE
        statement... not multiple sequential statements" requirement. Two
        statements total when both are requested in the same `PUT` is not a
        violation of that requirement: `documents` and `document_versions`
        are different tables with different primary keys, so no single
        literal SQL `UPDATE` can target both -- the requirement is about not
        splitting *same-table* field changes into separate round-trips."""
        document = self._session.execute(
            select(Document).where(Document.document_id == document_id)
        ).scalar_one_or_none()
        if document is None:
            raise DocumentNotFoundError(f"No documents row for {document_id}")

        now = datetime.now(UTC)
        # Not `dataclasses.replace(document, ...)` -- `Document` is a
        # SQLAlchemy declarative model, not a stdlib dataclass; merge the
        # requested changes into typed local variables instead of the ORM
        # instance.
        effective_lifecycle_state: str = document.lifecycle_state
        effective_authority_state: str | None = document.authority_state
        effective_updated_at = document.updated_at

        doc_values: dict[str, object] = {}
        if update.lifecycle_state is not None:
            doc_values["lifecycle_state"] = update.lifecycle_state
            effective_lifecycle_state = update.lifecycle_state
        if update.authority_state is not None:
            doc_values["authority_state"] = update.authority_state
            effective_authority_state = update.authority_state
        if doc_values:
            self._session.execute(
                sa_update(Document)
                .where(Document.document_id == document_id)
                .values(**doc_values, updated_at=now)
            )
            effective_updated_at = now

        version = self._session.execute(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document_id,
                DocumentVersion.is_committed == True,  # noqa: E712 -- SQL WHERE clause
                DocumentVersion.superseded_by_version_id.is_(None),
            )
        ).scalar_one_or_none()

        acl = _version_to_acl(version) if version is not None else None
        if update.acl is not None:
            if version is None or acl is None:
                # Unreachable via this MVP's only writer (ingest always
                # creates documents + document_versions together), but not
                # silently ignored if it ever happens -- fail loudly rather
                # than accept an ACL edit that has nowhere to persist.
                raise MissingAclVersionError(
                    f"No current document_versions row for {document_id} to apply ACL update"
                )
            acl_values, acl = _acl_update_values(acl, update.acl)
            if acl_values:
                self._session.execute(
                    sa_update(DocumentVersion)
                    .where(
                        DocumentVersion.document_id == document_id,
                        DocumentVersion.version_id == version.version_id,
                    )
                    .values(**acl_values)
                )

        return DocumentSummary(
            document_id=document.document_id,
            repository_id=document.repository_id,
            lifecycle_state=effective_lifecycle_state,
            authority_state=effective_authority_state,
            created_at=document.created_at,
            updated_at=effective_updated_at,
            acl=acl,
        )

    def _fetch_current_acl(self, document_ids: set[uuid.UUID]) -> dict[uuid.UUID, DocumentAcl]:
        if not document_ids:
            return {}
        rows = self._session.execute(
            select(DocumentVersion).where(
                DocumentVersion.document_id.in_(document_ids),
                DocumentVersion.is_committed == True,  # noqa: E712 -- SQL WHERE clause
                DocumentVersion.superseded_by_version_id.is_(None),
            )
        ).scalars().all()
        return {row.document_id: _version_to_acl(row) for row in rows}


class FakeDocumentStore:
    """In-memory fake for tests -- dict-backed, following this repo's
    established `Protocol` + fake pattern (`ingest/job_store.py`'s
    `InMemoryJobStore`). `seed()` lets a test populate rows directly, the
    same shape as `acl/ingest_stub.py`'s `FakeACLLookup.seed()`, since there
    is no admin "create document" route to drive this through HTTP."""

    def __init__(self) -> None:
        self._documents: dict[uuid.UUID, DocumentSummary] = {}

    def seed(self, summary: DocumentSummary) -> None:
        self._documents[summary.document_id] = summary

    def list_documents(self, *, cursor: str | None, limit: int) -> DocumentPage:
        rows = sorted(
            self._documents.values(), key=lambda d: (d.created_at, d.document_id), reverse=True
        )
        if cursor is not None:
            last_seen_timestamp, last_seen_id = decode_cursor(cursor)
            rows = [r for r in rows if (r.created_at, r.document_id) < (last_seen_timestamp, last_seen_id)]

        page_rows, next_cursor = _paginate(rows, limit)
        return DocumentPage(items=page_rows, next_cursor=next_cursor)

    def get_document(self, document_id: uuid.UUID) -> DocumentSummary | None:
        return self._documents.get(document_id)

    def update_document(self, document_id: uuid.UUID, update: DocumentUpdate) -> DocumentSummary:
        existing = self._documents.get(document_id)
        if existing is None:
            raise DocumentNotFoundError(f"No document {document_id}")

        acl = existing.acl
        if update.acl is not None:
            if acl is None:
                # Same distinction as SqlAlchemyDocumentStore's own raise
                # site: the document exists, only its ACL-bearing version is
                # missing -- a DocumentNotFoundError here would wrongly 404
                # as "no such document" (both stores implement one Protocol
                # and should agree on this).
                raise MissingAclVersionError(
                    f"No current ACL-bearing version seeded for {document_id} to apply ACL update"
                )
            _, acl = _acl_update_values(acl, update.acl)

        updated = replace(
            existing,
            lifecycle_state=(
                update.lifecycle_state if update.lifecycle_state is not None else existing.lifecycle_state
            ),
            authority_state=(
                update.authority_state if update.authority_state is not None else existing.authority_state
            ),
            acl=acl,
            updated_at=datetime.now(UTC),
        )
        self._documents[document_id] = updated
        return updated
