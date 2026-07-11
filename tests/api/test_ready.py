from fastapi.testclient import TestClient

from api.main import ServiceHealth, app

client = TestClient(app)


def test_ready_returns_dec117_schema_shape():
    """The response shape itself is correct now, independent of the values."""
    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"ready", "services"}
    assert set(body["services"].keys()) == set(ServiceHealth.model_fields)
    assert isinstance(body["ready"], bool)
    assert all(isinstance(v, bool) for v in body["services"].values())


def test_ready_reports_every_service_healthy():
    """DEC-117 target state — expected to fail until a later phase wires real
    health checks. This failure is intentional: Phase 1 has no backend
    services to check yet, so /ready honestly reports everything as not
    ready. A green result here would mean the test stopped checking the
    real target state, not that the feature is more done than it is."""
    response = client.get("/ready")
    body = response.json()

    assert body["ready"] is True
    assert all(body["services"].values())
