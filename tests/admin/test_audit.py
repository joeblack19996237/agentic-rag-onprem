"""Admin audit-list tests (TASK-033 Issue 04): `audit/event_store.py` (the
backing store) and `api/audit_routes.py` (`GET /v1/admin/audit`).

Store-level tiers (`.scratch/api-surface/issues/`
`04-admin-audit-model-version-read.md`'s "Testing tiers" section, same
split as Issue 03): Tier A (AC1) -- `SqlAlchemyAuditEventStore` against a
bare `mocker.MagicMock()` session, real compiled query asserted. Tier B
(AC2) -- `FakeAuditEventStore`, stateful across a sequence of calls.

HTTP-route-level tests (AC4 auth) use the `admin_client`/`audit_store`
fixtures from tests/admin/conftest.py.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from audit.event_store import FakeAuditEventStore, SqlAlchemyAuditEventStore, decode_cursor, encode_cursor
from audit.models import AuditEvent


def _make_event(
    audit_id: uuid.UUID | None = None,
    *,
    user_id: str = "user-1",
    timestamp: datetime | None = None,
    conversation_id: str = "conv-1",
) -> AuditEvent:
    return AuditEvent(
        audit_id=audit_id or uuid.uuid4(),
        conversation_id=conversation_id,
        user_id=user_id,
        session_id="session-1",
        query="what is the refund policy?",
        retrieved_chunk_ids=["chunk-1"],
        answer_text="the refund policy is...",
        citations=[],
        retrieval_safety_verdicts=None,
        safety_input_verdict=None,
        safety_output_verdict=None,
        verification_result={"grounded": True},
        refusal_reason_actual=None,
        refusal_reason_shown=None,
        intent="qa",
        context_fingerprint={},
        revision_count=0,
        policy_waiver_id=None,
        intent_class=None,
        nli_performed=True,
        latency_ms=250,
        timestamp=timestamp or datetime.now(UTC),
    )


def _mock_query_result(mocker, rows: Sequence[object]):  # type: ignore[no-untyped-def]
    result = mocker.MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


# ---- Tier A: SqlAlchemyAuditEventStore against a mocked Session ----


def test_lists_filtered_paginated_with_correct_where_clause(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    event = _make_event(user_id="user-42")
    session.execute.return_value = _mock_query_result(mocker, [event])
    from_ts = datetime(2026, 1, 1, tzinfo=UTC)
    to_ts = datetime(2026, 2, 1, tzinfo=UTC)

    store = SqlAlchemyAuditEventStore(session)
    page = store.list_events(from_ts=from_ts, to_ts=to_ts, user_id="user-42", cursor=None, limit=50)

    assert [item.audit_id for item in page.items] == [event.audit_id]
    assert page.next_cursor is None

    stmt = session.execute.call_args[0][0]
    compiled = str(stmt)
    assert "audit_events.timestamp >= " in compiled
    assert "audit_events.timestamp <= " in compiled
    assert "audit_events.user_id = " in compiled
    params = stmt.compile().params
    assert from_ts in params.values()
    assert to_ts in params.values()
    assert "user-42" in params.values()


def test_lists_omits_user_id_clause_when_not_filtering(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    session.execute.return_value = _mock_query_result(mocker, [])

    store = SqlAlchemyAuditEventStore(session)
    store.list_events(
        from_ts=datetime(2026, 1, 1, tzinfo=UTC),
        to_ts=datetime(2026, 2, 1, tzinfo=UTC),
        user_id=None,
        cursor=None,
        limit=50,
    )

    compiled = str(session.execute.call_args[0][0])
    # select(AuditEvent) always lists every column, including user_id, in
    # the SELECT clause -- the thing under test is the absence of a WHERE
    # filter on it, not the substring's absence from the compiled text.
    assert "audit_events.user_id = " not in compiled


def test_lists_orders_newest_first_with_stable_tiebreak(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    session.execute.return_value = _mock_query_result(mocker, [])

    store = SqlAlchemyAuditEventStore(session)
    store.list_events(
        from_ts=datetime(2026, 1, 1, tzinfo=UTC),
        to_ts=datetime(2026, 2, 1, tzinfo=UTC),
        user_id=None,
        cursor=None,
        limit=50,
    )

    compiled = str(session.execute.call_args[0][0])
    assert "ORDER BY audit_events.timestamp DESC, audit_events.audit_id DESC" in compiled


# ---- Tier B: FakeAuditEventStore, stateful across calls ----


def test_pagination_correct_under_interleaved_insert() -> None:
    store = FakeAuditEventStore()
    now = datetime.now(UTC)
    from_ts = now - timedelta(days=1)
    to_ts = now + timedelta(days=1)
    events = [_make_event(timestamp=now - timedelta(minutes=i)) for i in range(5)]
    for event in events:
        store.seed(event)

    page1 = store.list_events(from_ts=from_ts, to_ts=to_ts, user_id=None, cursor=None, limit=2)
    assert [item.audit_id for item in page1.items] == [events[0].audit_id, events[1].audit_id]
    assert page1.next_cursor is not None

    # A new row sorting *newest* is inserted between the two fetches --
    # keyset pagination anchors on the last-seen row, so it must not shift
    # page 2's contents or cause a skip/duplicate.
    new_event = _make_event(timestamp=now + timedelta(minutes=1))
    store.seed(new_event)

    page2 = store.list_events(from_ts=from_ts, to_ts=to_ts, user_id=None, cursor=page1.next_cursor, limit=2)
    assert [item.audit_id for item in page2.items] == [events[2].audit_id, events[3].audit_id]
    assert new_event.audit_id not in [item.audit_id for item in page2.items]

    page3 = store.list_events(from_ts=from_ts, to_ts=to_ts, user_id=None, cursor=page2.next_cursor, limit=2)
    assert [item.audit_id for item in page3.items] == [events[4].audit_id]
    assert page3.next_cursor is None


def test_fake_store_filters_by_from_to_and_user_id() -> None:
    store = FakeAuditEventStore()
    now = datetime.now(UTC)
    in_range_matching_user = _make_event(timestamp=now, user_id="user-1")
    in_range_other_user = _make_event(timestamp=now, user_id="user-2")
    out_of_range = _make_event(timestamp=now - timedelta(days=10), user_id="user-1")
    for event in (in_range_matching_user, in_range_other_user, out_of_range):
        store.seed(event)

    page = store.list_events(
        from_ts=now - timedelta(hours=1), to_ts=now + timedelta(hours=1), user_id="user-1", cursor=None, limit=50
    )

    assert [item.audit_id for item in page.items] == [in_range_matching_user.audit_id]


# ---- HTTP route tests: api/audit_routes.py, via admin_client (FakeAuditEventStore) ----


def _auth_headers(admin_api_key: str) -> dict[str, str]:
    return {"X-Admin-Api-Key": admin_api_key}


def test_route_returns_200_with_seeded_events(
    admin_client: TestClient, audit_store: FakeAuditEventStore, admin_api_key: str
) -> None:
    event = _make_event()
    audit_store.seed(event)

    response = admin_client.get(
        "/v1/admin/audit",
        params={"from": "2020-01-01T00:00:00Z", "to": "2030-01-01T00:00:00Z"},
        headers=_auth_headers(admin_api_key),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] is None
    assert len(body["items"]) == 1
    assert body["items"][0]["audit_id"] == str(event.audit_id)


def test_route_missing_from_returns_400(admin_client: TestClient, admin_api_key: str) -> None:
    response = admin_client.get(
        "/v1/admin/audit", params={"to": "2030-01-01T00:00:00Z"}, headers=_auth_headers(admin_api_key)
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_route_missing_to_returns_400(admin_client: TestClient, admin_api_key: str) -> None:
    response = admin_client.get(
        "/v1/admin/audit", params={"from": "2020-01-01T00:00:00Z"}, headers=_auth_headers(admin_api_key)
    )
    assert response.status_code == 400


def test_route_malformed_from_returns_400(admin_client: TestClient, admin_api_key: str) -> None:
    response = admin_client.get(
        "/v1/admin/audit",
        params={"from": "not-a-date", "to": "2030-01-01T00:00:00Z"},
        headers=_auth_headers(admin_api_key),
    )
    assert response.status_code == 400


def test_requires_auth_missing_credentials(admin_client: TestClient) -> None:
    response = admin_client.get(
        "/v1/admin/audit", params={"from": "2020-01-01T00:00:00Z", "to": "2030-01-01T00:00:00Z"}
    )
    assert response.status_code == 401


def test_requires_auth_invalid_admin_key(admin_client: TestClient) -> None:
    response = admin_client.get(
        "/v1/admin/audit",
        params={"from": "2020-01-01T00:00:00Z", "to": "2030-01-01T00:00:00Z"},
        headers={"X-Admin-Api-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_requires_auth_accepts_admin_key(admin_client: TestClient, admin_api_key: str) -> None:
    response = admin_client.get(
        "/v1/admin/audit",
        params={"from": "2020-01-01T00:00:00Z", "to": "2030-01-01T00:00:00Z"},
        headers=_auth_headers(admin_api_key),
    )
    assert response.status_code == 200


def test_requires_auth_accepts_jwt(admin_client: TestClient, jwt_headers: Callable[[], dict[str, str]]) -> None:
    response = admin_client.get(
        "/v1/admin/audit",
        params={"from": "2020-01-01T00:00:00Z", "to": "2030-01-01T00:00:00Z"},
        headers=jwt_headers(),
    )
    assert response.status_code == 200


def test_cursor_encode_decode_round_trips() -> None:
    ts = datetime.now(UTC)
    audit_id = uuid.uuid4()
    cursor = encode_cursor(last_seen_timestamp=ts, last_seen_id=audit_id)
    decoded_ts, decoded_id = decode_cursor(cursor)
    assert decoded_ts == ts
    assert decoded_id == audit_id
