"""Shared fixtures for tests/admin/ -- `client`/`keys`/`admin_api_key`/
`jwt_headers` come from tests/_shared_auth_fixtures.py (shared with
tests/api/); this file adds the admin-route-specific `document_store`/
`audit_store`/`admin_client` (Issue 03 + Issue 04's document/audit routes,
which share one dependency shape -- a Protocol-typed store swapped in via
`app.dependency_overrides`) and `mock_config_session`/`config_client`
(Issue 04's `/v1/admin/config/models`, which depends on `get_session`
directly rather than a store, since `list_active_model_versions` is a bare
function with one implementation, not a Protocol+fake pair). A real
conftest.py, auto-discovered by pytest.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from admin.document_store import FakeDocumentStore
from api.admin_routes import get_document_store
from api.audit_routes import get_audit_event_store
from api.ingest_routes import get_session
from api.main import app
from audit.event_store import FakeAuditEventStore
from tests._shared_auth_fixtures import admin_api_key as admin_api_key
from tests._shared_auth_fixtures import client as client
from tests._shared_auth_fixtures import jwt_headers as jwt_headers
from tests._shared_auth_fixtures import keys as keys


@pytest.fixture
def document_store() -> FakeDocumentStore:
    return FakeDocumentStore()


@pytest.fixture
def audit_store() -> FakeAuditEventStore:
    return FakeAuditEventStore()


@pytest.fixture
def admin_client(
    client: TestClient, document_store: FakeDocumentStore, audit_store: FakeAuditEventStore
) -> Iterator[TestClient]:
    """`client` plus every tests/admin/-domain dependency override. Cleans
    up `app.dependency_overrides` afterward, matching
    `tests/api/conftest.py`'s `ingest_client` fixture."""
    app.dependency_overrides[get_document_store] = lambda: document_store
    app.dependency_overrides[get_audit_event_store] = lambda: audit_store
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_document_store, None)
        app.dependency_overrides.pop(get_audit_event_store, None)


@pytest.fixture
def mock_config_session() -> MagicMock:
    """A bare mock, not a real Session -- no live Postgres in this sandbox.
    Every role's `get_active_model_version` call resolves to the same
    placeholder version; HTTP-level tests care about routing/auth/response
    shape, not per-role values (those are Tier A's job, mocked directly in
    tests/admin/test_config_models.py)."""
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "v1"
    return session


@pytest.fixture
def config_client(client: TestClient, mock_config_session: MagicMock) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: mock_config_session
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
