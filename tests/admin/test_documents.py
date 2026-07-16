"""Admin document tests (TASK-033 Issue 03): `admin/document_store.py` (the
backing store) and `api/admin_routes.py` (`GET`/`PUT /v1/admin/documents`).
Both live in this one file -- the issue's own Verification lines (e.g.
`pytest tests/admin/test_documents.py -k requires_auth -v`) all target this
path, matching `tests/api/test_ingest_routes.py`'s precedent of one file per
route module rather than splitting store-level and HTTP-level tests apart.

Two non-interchangeable store-level tiers (`.scratch/api-surface/issues/`
`03-admin-document-management.md`'s "Testing tiers" section):

- **Tier A** (AC1, AC3, AC5): `SqlAlchemyDocumentStore` against a bare
  `mocker.MagicMock()` session (the pattern `tests/config/test_active_model_version.py`
  established) -- proves the real code builds syntactically/referentially
  correct SQL for a single call. Does not prove multi-call behavior.
- **Tier B** (AC2, AC4): `FakeDocumentStore`, stateful across a sequence of
  calls within one test -- proves the pagination/persistence *algorithm*.
  Does not touch SQLAlchemy at all.

HTTP-route-level tests (AC6 auth, request validation, route wiring) use the
`admin_client`/`document_store` fixtures from tests/admin/conftest.py
instead (a `FakeDocumentStore` behind `app.dependency_overrides`).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Callable

import pytest
from fastapi.testclient import TestClient

from admin.document_store import (
    AclUpdate,
    DocumentNotFoundError,
    DocumentSummary,
    DocumentUpdate,
    FakeDocumentStore,
    SqlAlchemyDocumentStore,
    _version_to_acl,
    decode_cursor,
    encode_cursor,
)
from ingest.models import Document, DocumentVersion


def _make_document(
    document_id: uuid.UUID | None = None,
    *,
    repository_id: str = "default",
    lifecycle_state: str = "active",
    authority_state: str | None = None,
    created_at: datetime | None = None,
) -> Document:
    now = created_at or datetime.now(UTC)
    return Document(
        document_id=document_id or uuid.uuid4(),
        repository_id=repository_id,
        lifecycle_state=lifecycle_state,
        authority_state=authority_state,
        created_at=now,
        updated_at=now,
    )


def _make_version(
    document_id: uuid.UUID,
    *,
    allow_principals: list[str] | None = None,
    deny_principals: list[str] | None = None,
    security_label: str = "internal",
    retention_state: str = "active",
) -> DocumentVersion:
    return DocumentVersion(
        document_id=document_id,
        version_id=str(uuid.uuid4()),
        is_committed=True,
        security_label=security_label,
        retention_state=retention_state,
        allow_principals=allow_principals if allow_principals is not None else ["group:eng"],
        deny_principals=deny_principals if deny_principals is not None else [],
        superseded_by_version_id=None,
        ingested_at=datetime.now(UTC),
    )


def _mock_query_result(mocker, rows: Sequence[object]):  # type: ignore[no-untyped-def]
    result = mocker.MagicMock()
    result.scalars.return_value.all.return_value = rows
    result.scalar_one_or_none.return_value = rows[0] if rows else None
    return result


# ---- Tier A: SqlAlchemyDocumentStore against a mocked Session ----


def test_lists_paginated_with_correct_order_by_and_null_cursor_on_last_page(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    doc = _make_document()
    session.execute.side_effect = [_mock_query_result(mocker, [doc]), _mock_query_result(mocker, [])]

    store = SqlAlchemyDocumentStore(session)
    page = store.list_documents(cursor=None, limit=50)

    assert [item.document_id for item in page.items] == [doc.document_id]
    assert page.next_cursor is None

    compiled = str(session.execute.call_args_list[0][0][0])
    assert "FROM documents" in compiled
    assert "ORDER BY documents.created_at DESC, documents.document_id DESC" in compiled


def test_lists_sets_next_cursor_when_a_page_boundary_is_crossed(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    docs = [_make_document(created_at=datetime.now(UTC) - timedelta(minutes=i)) for i in range(3)]
    # limit=2 requested; the store peeks limit+1 -- 3 rows back means "more exist".
    session.execute.side_effect = [_mock_query_result(mocker, docs), _mock_query_result(mocker, [])]

    store = SqlAlchemyDocumentStore(session)
    page = store.list_documents(cursor=None, limit=2)

    assert len(page.items) == 2
    assert page.next_cursor is not None
    last_seen_timestamp, last_seen_id = decode_cursor(page.next_cursor)
    assert last_seen_id == docs[1].document_id
    assert last_seen_timestamp == docs[1].created_at


def test_lists_applies_cursor_as_a_tuple_comparison_where_clause(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    session.execute.side_effect = [_mock_query_result(mocker, []), _mock_query_result(mocker, [])]
    cursor_ts = datetime.now(UTC)
    cursor_id = uuid.uuid4()
    cursor = encode_cursor(last_seen_timestamp=cursor_ts, last_seen_id=cursor_id)

    store = SqlAlchemyDocumentStore(session)
    store.list_documents(cursor=cursor, limit=50)

    stmt = session.execute.call_args_list[0][0][0]
    compiled = str(stmt)
    assert "WHERE (documents.created_at, documents.document_id) < " in compiled
    params = stmt.compile().params
    assert cursor_ts in params.values()
    assert cursor_id in params.values()


def test_soft_delete_issues_update_not_delete(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    doc = _make_document(lifecycle_state="active")
    session.execute.side_effect = [
        _mock_query_result(mocker, [doc]),  # existence-check SELECT
        mocker.MagicMock(),  # UPDATE documents
        _mock_query_result(mocker, []),  # current-version SELECT (no acl requested)
    ]

    store = SqlAlchemyDocumentStore(session)
    result = store.update_document(doc.document_id, DocumentUpdate(lifecycle_state="deleted"))

    assert result.lifecycle_state == "deleted"
    update_call = session.execute.call_args_list[1][0][0]
    compiled_update = str(update_call)
    assert compiled_update.startswith("UPDATE documents SET")
    assert "DELETE" not in compiled_update.upper()
    params = update_call.compile().params
    assert params["lifecycle_state"] == "deleted"
    assert params["document_id_1"] == doc.document_id


def test_combined_lifecycle_state_and_acl_update_issues_one_update_per_table(mocker) -> None:  # type: ignore[no-untyped-def]
    """Closes a gap the Spec-axis code review found, 2026-07-16: no test
    exercised a `PUT` changing both a `documents`-table field and the `acl`
    (`document_versions`-table) in one call -- exactly the combination
    `update_document`'s own docstring argues about ("two statements total...
    is not a violation... different tables, different primary keys")."""
    session = mocker.MagicMock()
    doc = _make_document(lifecycle_state="active")
    version = _make_version(doc.document_id, allow_principals=["group:eng"])
    session.execute.side_effect = [
        _mock_query_result(mocker, [doc]),  # existence-check SELECT (documents)
        mocker.MagicMock(),  # UPDATE documents
        _mock_query_result(mocker, [version]),  # current-version SELECT (document_versions)
        mocker.MagicMock(),  # UPDATE document_versions
    ]

    store = SqlAlchemyDocumentStore(session)
    result = store.update_document(
        doc.document_id,
        DocumentUpdate(
            lifecycle_state="deleted", acl=AclUpdate(allow_principals=["group:eng", "group:legal"])
        ),
    )

    assert result.lifecycle_state == "deleted"
    assert result.acl is not None
    assert result.acl.allow_principals == ["group:eng", "group:legal"]

    # One UPDATE per table, each covering every changed field for that
    # table in a single call -- never more than one UPDATE per table.
    assert session.execute.call_count == 4
    doc_update = session.execute.call_args_list[1][0][0]
    assert str(doc_update).startswith("UPDATE documents SET")
    assert doc_update.compile().params["lifecycle_state"] == "deleted"

    version_update = session.execute.call_args_list[3][0][0]
    assert str(version_update).startswith("UPDATE document_versions SET")
    assert version_update.compile().params["allow_principals"] == ["group:eng", "group:legal"]


def test_unknown_id_returns_404_not_an_exception(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None

    store = SqlAlchemyDocumentStore(session)
    with pytest.raises(DocumentNotFoundError):
        store.update_document(uuid.uuid4(), DocumentUpdate(lifecycle_state="deleted"))

    # Only the existence-check SELECT ran -- no UPDATE was ever attempted
    # against a document_id that doesn't exist.
    assert session.execute.call_count == 1


# ---- Tier B: FakeDocumentStore, stateful across calls ----


def test_pagination_correct_under_interleaved_insert() -> None:
    store = FakeDocumentStore()
    now = datetime.now(UTC)
    docs = [_make_document(created_at=now - timedelta(minutes=i)) for i in range(5)]
    for doc in docs:
        store.seed(_to_summary(doc))

    page1 = store.list_documents(cursor=None, limit=2)
    assert [item.document_id for item in page1.items] == [docs[0].document_id, docs[1].document_id]
    assert page1.next_cursor is not None

    # A new row sorting *newest* is inserted between the two fetches --
    # keyset pagination anchors on the last-seen row, so it must not shift
    # page 2's contents or cause a skip/duplicate.
    new_doc = _make_document(created_at=now + timedelta(minutes=1))
    store.seed(_to_summary(new_doc))

    page2 = store.list_documents(cursor=page1.next_cursor, limit=2)
    assert [item.document_id for item in page2.items] == [docs[2].document_id, docs[3].document_id]
    assert new_doc.document_id not in [item.document_id for item in page2.items]

    page3 = store.list_documents(cursor=page2.next_cursor, limit=2)
    assert [item.document_id for item in page3.items] == [docs[4].document_id]
    assert page3.next_cursor is None


def test_acl_edit_persists_observable_on_a_subsequent_get() -> None:
    store = FakeDocumentStore()
    doc = _make_document()
    version = _make_version(doc.document_id, allow_principals=["group:eng"], deny_principals=[])
    store.seed(_to_summary(doc, version))

    store.update_document(
        doc.document_id,
        DocumentUpdate(acl=AclUpdate(allow_principals=["group:eng", "group:finance"], deny_principals=["user:x"])),
    )

    fetched = store.get_document(doc.document_id)
    assert fetched is not None
    assert fetched.acl is not None
    assert fetched.acl.allow_principals == ["group:eng", "group:finance"]
    assert fetched.acl.deny_principals == ["user:x"]
    # security_label/retention_state weren't part of this PUT -- untouched.
    assert fetched.acl.security_label == version.security_label


def test_fake_store_unknown_id_raises_not_found() -> None:
    store = FakeDocumentStore()
    with pytest.raises(DocumentNotFoundError):
        store.update_document(uuid.uuid4(), DocumentUpdate(lifecycle_state="deleted"))


def _to_summary(document: Document, version: DocumentVersion | None = None) -> DocumentSummary:
    acl = _version_to_acl(version) if version is not None else None
    return DocumentSummary(
        document_id=document.document_id,
        repository_id=document.repository_id,
        lifecycle_state=document.lifecycle_state,
        authority_state=document.authority_state,
        created_at=document.created_at,
        updated_at=document.updated_at,
        acl=acl,
    )


# ---- HTTP route tests: api/admin_routes.py, via admin_client (FakeDocumentStore) ----


def _auth_headers(admin_api_key: str) -> dict[str, str]:
    return {"X-Admin-Api-Key": admin_api_key}


def test_list_returns_200_with_seeded_items(
    admin_client: TestClient, document_store: FakeDocumentStore, admin_api_key: str
) -> None:
    doc = _make_document()
    version = _make_version(doc.document_id)
    document_store.seed(_to_summary(doc, version))

    response = admin_client.get("/v1/admin/documents", headers=_auth_headers(admin_api_key))

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] is None
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["document_id"] == str(doc.document_id)
    assert item["acl"]["allow_principals"] == version.allow_principals


def test_put_soft_delete_returns_updated_document(
    admin_client: TestClient, document_store: FakeDocumentStore, admin_api_key: str
) -> None:
    doc = _make_document(lifecycle_state="active")
    document_store.seed(_to_summary(doc))

    response = admin_client.put(
        f"/v1/admin/documents/{doc.document_id}",
        json={"lifecycle_state": "deleted"},
        headers=_auth_headers(admin_api_key),
    )

    assert response.status_code == 200
    assert response.json()["lifecycle_state"] == "deleted"


def test_put_acl_edit_returns_updated_document(
    admin_client: TestClient, document_store: FakeDocumentStore, admin_api_key: str
) -> None:
    doc = _make_document()
    version = _make_version(doc.document_id, allow_principals=["group:eng"])
    document_store.seed(_to_summary(doc, version))

    response = admin_client.put(
        f"/v1/admin/documents/{doc.document_id}",
        json={"acl": {"allow_principals": ["group:eng", "group:legal"]}},
        headers=_auth_headers(admin_api_key),
    )

    assert response.status_code == 200
    assert response.json()["acl"]["allow_principals"] == ["group:eng", "group:legal"]


def test_put_unknown_id_returns_404(admin_client: TestClient, admin_api_key: str) -> None:
    response = admin_client.put(
        f"/v1/admin/documents/{uuid.uuid4()}",
        json={"lifecycle_state": "deleted"},
        headers=_auth_headers(admin_api_key),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_put_empty_body_returns_400(
    admin_client: TestClient, document_store: FakeDocumentStore, admin_api_key: str
) -> None:
    doc = _make_document()
    document_store.seed(_to_summary(doc))

    response = admin_client.put(
        f"/v1/admin/documents/{doc.document_id}", json={}, headers=_auth_headers(admin_api_key)
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_put_invalid_lifecycle_state_returns_400(
    admin_client: TestClient, document_store: FakeDocumentStore, admin_api_key: str
) -> None:
    doc = _make_document()
    document_store.seed(_to_summary(doc))

    response = admin_client.put(
        f"/v1/admin/documents/{doc.document_id}",
        json={"lifecycle_state": "active"},  # only "deleted" is accepted -- no undelete path
        headers=_auth_headers(admin_api_key),
    )

    assert response.status_code == 400


def test_put_invalid_authority_state_returns_400(
    admin_client: TestClient, document_store: FakeDocumentStore, admin_api_key: str
) -> None:
    doc = _make_document()
    document_store.seed(_to_summary(doc))

    response = admin_client.put(
        f"/v1/admin/documents/{doc.document_id}",
        json={"authority_state": "not-a-real-state"},
        headers=_auth_headers(admin_api_key),
    )

    assert response.status_code == 400


def test_requires_auth_list_missing_credentials(admin_client: TestClient) -> None:
    response = admin_client.get("/v1/admin/documents")
    assert response.status_code == 401


def test_requires_auth_list_invalid_admin_key(admin_client: TestClient) -> None:
    response = admin_client.get("/v1/admin/documents", headers={"X-Admin-Api-Key": "wrong-key"})
    assert response.status_code == 401


def test_requires_auth_list_accepts_admin_key(admin_client: TestClient, admin_api_key: str) -> None:
    response = admin_client.get("/v1/admin/documents", headers=_auth_headers(admin_api_key))
    assert response.status_code == 200


def test_requires_auth_list_accepts_jwt(
    admin_client: TestClient, jwt_headers: Callable[[], dict[str, str]]
) -> None:
    response = admin_client.get("/v1/admin/documents", headers=jwt_headers())
    assert response.status_code == 200


def test_requires_auth_put_missing_credentials(
    admin_client: TestClient, document_store: FakeDocumentStore
) -> None:
    doc = _make_document()
    document_store.seed(_to_summary(doc))

    response = admin_client.put(f"/v1/admin/documents/{doc.document_id}", json={"lifecycle_state": "deleted"})

    assert response.status_code == 401


def test_requires_auth_put_invalid_admin_key(
    admin_client: TestClient, document_store: FakeDocumentStore
) -> None:
    doc = _make_document()
    document_store.seed(_to_summary(doc))

    response = admin_client.put(
        f"/v1/admin/documents/{doc.document_id}",
        json={"lifecycle_state": "deleted"},
        headers={"X-Admin-Api-Key": "wrong-key"},
    )

    assert response.status_code == 401


def test_requires_auth_put_accepts_admin_key(
    admin_client: TestClient, document_store: FakeDocumentStore, admin_api_key: str
) -> None:
    doc = _make_document()
    document_store.seed(_to_summary(doc))

    response = admin_client.put(
        f"/v1/admin/documents/{doc.document_id}",
        json={"lifecycle_state": "deleted"},
        headers=_auth_headers(admin_api_key),
    )

    assert response.status_code == 200


def test_requires_auth_put_accepts_jwt(
    admin_client: TestClient, document_store: FakeDocumentStore, jwt_headers: Callable[[], dict[str, str]]
) -> None:
    doc = _make_document()
    document_store.seed(_to_summary(doc))

    response = admin_client.put(
        f"/v1/admin/documents/{doc.document_id}", json={"lifecycle_state": "deleted"}, headers=jwt_headers()
    )

    assert response.status_code == 200
