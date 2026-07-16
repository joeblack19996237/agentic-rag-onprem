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
    # Mutates shared `app.state` directly (the only way to exercise "no
    # JWKS/admin key configured" -- `require_auth` reads `request.app.state`
    # itself, not a `Depends()`-injected value `app.dependency_overrides`
    # could swap). Restored in `finally` so this doesn't leak into whichever
    # test happens to run next (test-audit, 2026-07-16) -- every other test
    # in this suite goes through the `client` fixture, which happens to
    # reset both values on every call, but this test doesn't use that
    # fixture and shouldn't rely on a different test's setup to clean up
    # after it.
    previous_jwks = app.state.jwks
    previous_admin_api_key = app.state.admin_api_key
    app.state.jwks = None
    app.state.admin_api_key = None
    try:
        client = TestClient(app)
        response = client.post("/v1/query", json={"query": "hello"})

        assert response.status_code == 401
        assert response.status_code != 404
    finally:
        app.state.jwks = previous_jwks
        app.state.admin_api_key = previous_admin_api_key
