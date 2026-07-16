"""Shared fixtures for tests/admin/ -- `client`/`keys`/`admin_api_key`/
`jwt_headers` come from tests/_shared_auth_fixtures.py (shared with
tests/api/); this file adds the admin-route-specific `document_store`/
`admin_client` fixtures. A real conftest.py, auto-discovered by pytest.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from admin.document_store import FakeDocumentStore
from api.admin_routes import get_document_store
from api.main import app
from tests._shared_auth_fixtures import admin_api_key as admin_api_key
from tests._shared_auth_fixtures import client as client
from tests._shared_auth_fixtures import jwt_headers as jwt_headers
from tests._shared_auth_fixtures import keys as keys


@pytest.fixture
def document_store() -> FakeDocumentStore:
    return FakeDocumentStore()


@pytest.fixture
def admin_client(client: TestClient, document_store: FakeDocumentStore) -> Iterator[TestClient]:
    """`client` plus the admin-route dependency override. Cleans up
    `app.dependency_overrides` afterward, matching `tests/api/conftest.py`'s
    `ingest_client` fixture."""
    app.dependency_overrides[get_document_store] = lambda: document_store
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_document_store, None)
