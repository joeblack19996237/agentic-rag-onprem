"""Ingest HTTP route tests (TASK-033 Issue 02): `POST /v1/ingest` +
`GET /v1/ingest/{document_id}`, wired to `ingest/pipeline.py`'s already-built
pipeline. `client`/`ingest_client`/`fake_pipeline_deps`/`fake_scheduler`/
`job_store`/`mock_session`/`admin_api_key` fixtures live in
tests/api/conftest.py.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from api.ingest_routes import ACLOverride
from ingest.job_store import InMemoryJobStore
from ingest.task_scheduler import FakeTaskScheduler

VALID_ACL_OVERRIDE = json.dumps(
    {"allow_principals": ["group:eng"], "deny_principals": [], "security_label": "internal"}
)


def _auth_headers(admin_api_key: str) -> dict[str, str]:
    return {"X-Admin-Api-Key": admin_api_key}


def _upload(
    client: TestClient,
    admin_api_key: str,
    *,
    content_type: str = "text/plain",
    filename: str = "doc.txt",
    content: bytes = b"hello world",
    acl_override: str | None = VALID_ACL_OVERRIDE,
    repository_id: str = "default",
    headers: dict[str, str] | None = None,
):
    data = {"repository_id": repository_id}
    if acl_override is not None:
        data["acl_override"] = acl_override
    return client.post(
        "/v1/ingest",
        files={"file": (filename, content, content_type)},
        data=data,
        headers=_auth_headers(admin_api_key) if headers is None else headers,
    )


def test_schedules_background(
    ingest_client: TestClient,
    admin_api_key: str,
    fake_scheduler: FakeTaskScheduler,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        response = _upload(ingest_client, admin_api_key)

    assert response.status_code == 200
    assert len(fake_scheduler.scheduled) == 1
    assert "scheduled for background processing" in caplog.text
    assert "TASK-010" in caplog.text


def test_returns_document_id_and_status_url(ingest_client: TestClient, admin_api_key: str) -> None:
    response = _upload(ingest_client, admin_api_key)

    assert response.status_code == 200
    body = response.json()
    assert "document_id" in body
    assert body["status_url"] == f"/v1/ingest/{body['document_id']}"
    assert body["status_url"].startswith("/v1/ingest/")
    assert not body["status_url"].startswith("http")


def test_rejects_unsupported_mime_type(
    ingest_client: TestClient, admin_api_key: str, fake_scheduler: FakeTaskScheduler
) -> None:
    response = _upload(ingest_client, admin_api_key, content_type="image/png", filename="doc.png")

    assert response.status_code == 415
    body = response.json()
    assert body["error"]["code"] == "unsupported_media_type"
    supported = body["error"]["details"]["supported_formats"]
    assert "text/plain" in supported
    assert "application/pdf" in supported
    assert len(fake_scheduler.scheduled) == 0


def test_missing_acl_override_returns_400(ingest_client: TestClient, admin_api_key: str) -> None:
    response = _upload(ingest_client, admin_api_key, acl_override=None)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_invalid_acl_override_returns_400(ingest_client: TestClient, admin_api_key: str) -> None:
    response = _upload(ingest_client, admin_api_key, acl_override="not valid json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.parametrize(
    ("seeded_phase", "seeded_progress", "expected_status"),
    [
        ("pending", 0.0, "pending"),
        ("parsed", 0.2, "parsing"),
        ("chunked", 0.4, "parsing"),
        ("indexing", 0.7, "indexing"),
        ("ready", 1.0, "ready"),
        ("failed", 0.4, "failed"),
    ],
)
def test_status_mapping(
    ingest_client: TestClient,
    admin_api_key: str,
    job_store: InMemoryJobStore,
    seeded_phase: str,
    seeded_progress: float,
    expected_status: str,
) -> None:
    job_id = job_store.create_job("ingest")
    job_store.advance(job_id, {"phase": seeded_phase, "progress": seeded_progress})
    if seeded_phase == "failed":
        job_store.advance(job_id, {"errors": ["some internal stack trace, /etc/secret/path"]})

    response = ingest_client.get(f"/v1/ingest/{job_id}", headers=_auth_headers(admin_api_key))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == expected_status
    assert body["progress"] == seeded_progress
    if expected_status == "failed":
        # Redaction: the raw internal error text must never cross the HTTP
        # boundary (docs/coding-standards.md's error-handling rule; flagged
        # in advance by JobStore.fail()'s own docstring, code review 2026-07-15).
        assert "internal stack trace" not in json.dumps(body)
        assert "/etc/secret/path" not in json.dumps(body)
        assert len(body["errors"]) == 1
    else:
        assert body["errors"] == []


def test_unknown_id_returns_404(ingest_client: TestClient, admin_api_key: str) -> None:
    response = ingest_client.get(
        "/v1/ingest/00000000-0000-0000-0000-000000000000", headers=_auth_headers(admin_api_key)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_requires_auth_post_missing_credentials(ingest_client: TestClient, admin_api_key: str) -> None:
    response = _upload(ingest_client, admin_api_key, headers={})
    assert response.status_code == 401


def test_requires_auth_post_invalid_admin_key(ingest_client: TestClient, admin_api_key: str) -> None:
    response = _upload(ingest_client, admin_api_key, headers={"X-Admin-Api-Key": "wrong-key"})
    assert response.status_code == 401


def test_requires_auth_post_accepts_admin_key(ingest_client: TestClient, admin_api_key: str) -> None:
    response = _upload(ingest_client, admin_api_key)
    assert response.status_code == 200


def test_requires_auth_post_accepts_jwt(
    ingest_client: TestClient, jwt_headers: Callable[[], dict[str, str]]
) -> None:
    response = _upload(ingest_client, "", headers=jwt_headers())
    assert response.status_code == 200


def test_requires_auth_get_missing_credentials(ingest_client: TestClient) -> None:
    response = ingest_client.get("/v1/ingest/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401


def test_requires_auth_get_accepts_jwt(
    ingest_client: TestClient, jwt_headers: Callable[[], dict[str, str]], job_store: InMemoryJobStore
) -> None:
    job_id = job_store.create_job("ingest")
    response = ingest_client.get(f"/v1/ingest/{job_id}", headers=jwt_headers())
    assert response.status_code == 200


def test_acl_override_shape_requires_security_label() -> None:
    with pytest.raises(Exception):
        ACLOverride.model_validate({"allow_principals": ["x"]})
