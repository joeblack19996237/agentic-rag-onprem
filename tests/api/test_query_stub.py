"""POST /v1/query stub (TASK-033 Issue 01): registered, auth-enforced,
returns 501 with the standard structured error body -- not a bare/unstructured
501, and not 404. Real generation logic lands in Phase 3 (TASK-011+); this
file only covers the stub's own contract, not query semantics. `client`/
`admin_api_key` fixtures live in tests/api/conftest.py.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_query_stub_returns_structured_501_for_authenticated_request(
    client: TestClient, admin_api_key: str
) -> None:
    response = client.post("/v1/query", json={"query": "hello"}, headers={"X-Admin-Api-Key": admin_api_key})

    assert response.status_code == 501
    body = response.json()
    assert body["error"]["code"] == "not_implemented"
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert "request_id" in body["error"]


def test_query_stub_registered_in_openapi_schema() -> None:
    schema = app.openapi()
    assert "/v1/query" in schema["paths"]
    assert "post" in schema["paths"]["/v1/query"]


def test_query_stub_unauthenticated_request_is_401_not_404() -> None:
    app.state.jwks = None
    app.state.admin_api_key = None
    client = TestClient(app)

    response = client.post("/v1/query", json={"query": "hello"})

    assert response.status_code == 401
    assert response.status_code != 404
