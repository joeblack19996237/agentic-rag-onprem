"""Tests for ingest/job_store.py -- the job-store port, its in-memory
fake, and the real Postgres-backed implementation's payload-mapping
logic (structural correctness only; round-tripping against a live
server is [manual-verify], no live Postgres in this sandbox)."""

from __future__ import annotations

import uuid

import pytest

from ingest.job_store import InMemoryJobStore, SqlAlchemyJobStore
from ingest.models import JobQueue


def test_in_memory_job_store_create_job_starts_pending() -> None:
    store = InMemoryJobStore()
    job_id = store.create_job("ingest")
    assert store.get_payload(job_id) == {"phase": "pending", "progress": 0.0}
    assert store.get_status(job_id) == "pending"


def test_in_memory_job_store_advance_merges_payload_and_marks_in_progress() -> None:
    store = InMemoryJobStore()
    job_id = store.create_job("ingest")

    store.advance(job_id, {"phase": "chunked", "progress": 0.4, "checkpoint_path": "x.json"})

    assert store.get_payload(job_id) == {
        "phase": "chunked",
        "progress": 0.4,
        "checkpoint_path": "x.json",
    }
    assert store.get_status(job_id) == "in_progress"


def test_in_memory_job_store_advance_does_not_drop_earlier_keys() -> None:
    store = InMemoryJobStore()
    job_id = store.create_job("ingest")
    store.advance(job_id, {"phase": "chunked", "parsed_checkpoint_path": "parsed.json"})
    # A later advance() touching different keys must not clobber the
    # earlier ones -- this is what "does not drop earlier keys" actually
    # asserts (fixed 2026-07-15: the original version only checked the
    # key both calls overwrote, which would pass even if advance()
    # replaced the whole payload dict instead of merging into it).
    store.advance(job_id, {"phase": "indexing", "chunked_checkpoint_path": "chunked.json"})

    payload = store.get_payload(job_id)
    assert payload["phase"] == "indexing"
    assert payload["parsed_checkpoint_path"] == "parsed.json"
    assert payload["chunked_checkpoint_path"] == "chunked.json"


def test_in_memory_job_store_complete_sets_ready_phase() -> None:
    store = InMemoryJobStore()
    job_id = store.create_job("ingest")
    store.complete(job_id)
    assert store.get_payload(job_id)["phase"] == "ready"
    assert store.get_payload(job_id)["progress"] == 1.0
    assert store.get_status(job_id) == "complete"


def test_in_memory_job_store_fail_records_error_and_status() -> None:
    store = InMemoryJobStore()
    job_id = store.create_job("ingest")
    store.fail(job_id, "embedding service unreachable")
    assert store.get_payload(job_id)["phase"] == "failed"
    assert store.get_payload(job_id)["errors"] == ["embedding service unreachable"]
    assert store.get_status(job_id) == "failed"


def test_sqlalchemy_job_store_create_job_adds_a_job_queue_row(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    store = SqlAlchemyJobStore(session)

    job_id = store.create_job("ingest")

    assert isinstance(job_id, uuid.UUID)
    added = session.add.call_args[0][0]
    assert isinstance(added, JobQueue)
    assert added.job_id == job_id
    assert added.job_type == "ingest"
    assert added.status == "pending"
    assert added.payload == {"phase": "pending", "progress": 0.0}
    session.flush.assert_called_once()


def test_sqlalchemy_job_store_advance_merges_payload_on_the_fetched_row(mocker) -> None:  # type: ignore[no-untyped-def]
    job_id = uuid.uuid4()
    row = JobQueue(job_id=job_id, job_type="ingest", payload={"phase": "pending", "progress": 0.0}, status="pending")
    session = mocker.MagicMock()
    session.get.return_value = row

    store = SqlAlchemyJobStore(session)
    store.advance(job_id, {"phase": "chunked", "progress": 0.4})

    assert row.payload == {"phase": "chunked", "progress": 0.4}
    assert row.status == "in_progress"
    session.get.assert_called_once_with(JobQueue, job_id)


def test_sqlalchemy_job_store_raises_when_job_not_found(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    session.get.return_value = None
    store = SqlAlchemyJobStore(session)

    with pytest.raises(LookupError):
        store.get_payload(uuid.uuid4())
