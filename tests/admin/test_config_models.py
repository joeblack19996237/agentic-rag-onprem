"""Admin config-models tests (TASK-033 Issue 04): `config/active_model_version.py`'s
`list_active_model_versions` and `api/config_routes.py`'s
`GET /v1/admin/config/models`.

Tier A (AC3) -- `list_active_model_versions` against a bare
`mocker.MagicMock()` session, the same pattern `tests/config/`
`test_active_model_version.py` already established for the single-role
query this extends. No Tier B here -- unlike Issue 03's `PUT`/Issue 04's
`GET /v1/admin/audit`, there's no multi-call persistence/pagination
algorithm to prove against known data, just a loop over a fixed role list.

HTTP-route-level tests (AC4 auth) use `config_client`/`mock_config_session`
from tests/admin/conftest.py.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from config.active_model_version import KNOWN_ROLES, list_active_model_versions


def _mock_query_result(mocker, value: object):  # type: ignore[no-untyped-def]
    result = mocker.MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


# ---- Tier A: list_active_model_versions against a mocked Session ----


def test_lists_active_version_per_role(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    session.execute.side_effect = [
        _mock_query_result(mocker, f"{role}-v1") for role in KNOWN_ROLES
    ]

    results = list_active_model_versions(session)

    assert len(results) == len(KNOWN_ROLES)
    assert [r.role for r in results] == KNOWN_ROLES
    assert all(r.model_version == f"{r.role}-v1" for r in results)


def test_missing_active_version_for_one_role_does_not_fail_the_whole_request(
    mocker, caplog: pytest.LogCaptureFixture
) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    # "policy" (last role) has no active row; every other role does.
    mock_results = [_mock_query_result(mocker, f"{role}-v1") for role in KNOWN_ROLES[:-1]]
    mock_results.append(_mock_query_result(mocker, None))
    session.execute.side_effect = mock_results

    with caplog.at_level("WARNING"):
        results = list_active_model_versions(session)

    assert len(results) == len(KNOWN_ROLES)
    by_role = {r.role: r.model_version for r in results}
    assert by_role["policy"] is None
    assert all(v is not None for role, v in by_role.items() if role != "policy")
    assert "policy" in caplog.text


# ---- HTTP route tests: api/config_routes.py, via config_client (mocked Session) ----


def test_route_returns_200_with_all_roles(config_client: TestClient, admin_api_key: str) -> None:
    response = config_client.get("/v1/admin/config/models", headers={"X-Admin-Api-Key": admin_api_key})

    assert response.status_code == 200
    body = response.json()
    assert {m["role"] for m in body["models"]} == set(KNOWN_ROLES)


def test_requires_auth_missing_credentials(config_client: TestClient) -> None:
    response = config_client.get("/v1/admin/config/models")
    assert response.status_code == 401


def test_requires_auth_invalid_admin_key(config_client: TestClient) -> None:
    response = config_client.get("/v1/admin/config/models", headers={"X-Admin-Api-Key": "wrong-key"})
    assert response.status_code == 401


def test_requires_auth_accepts_admin_key(config_client: TestClient, admin_api_key: str) -> None:
    response = config_client.get("/v1/admin/config/models", headers={"X-Admin-Api-Key": admin_api_key})
    assert response.status_code == 200


def test_requires_auth_accepts_jwt(
    config_client: TestClient, jwt_headers: Callable[[], dict[str, str]]
) -> None:
    response = config_client.get("/v1/admin/config/models", headers=jwt_headers())
    assert response.status_code == 200
