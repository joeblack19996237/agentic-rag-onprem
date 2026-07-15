"""Job-store seam: a narrow port for job creation and checkpoint
bookkeeping, with a real Postgres-backed implementation and an
in-memory fake.

`job_queue.status` (`CHECK IN (pending, in_progress, complete, failed)`,
TASK-006) is generic dispatch bookkeeping shared with CDC jobs -- it is
not the ingest-specific `pending -> parsing -> indexing -> ready`
progression the API contract (`specs/06-api-contracts.md`) exposes. That
finer-grained phase, a progress fraction, and small flags (e.g.
`parser_fallback`) live inside `job_queue.payload` (JSONB) instead --
kept lightweight, never the bulk step output itself; see
`ingest/checkpoints.py` for where bulk data actually lives.

The real Postgres-backed implementation's correctness against a live
server is `[manual-verify]` (this sandbox has no Docker/live Postgres,
`docs/agents/dev-environment.md`) -- the in-memory fake is what the
Tier-1 acceptance criteria actually exercise.
"""

from __future__ import annotations

import uuid
from typing import Literal, Protocol

from sqlalchemy.orm import Session

from ingest.models import JobQueue

# The ingest-specific phase progression this payload tracks -- a fixed
# vocabulary, not a bare string (code-review finding, 2026-07-15).
JobPhase = Literal["pending", "parsed", "chunked", "indexing", "ready", "failed"]

_INITIAL_PAYLOAD: dict[str, object] = {"phase": "pending", "progress": 0.0}


class JobStore(Protocol):
    def create_job(self, job_type: str) -> uuid.UUID: ...

    def get_payload(self, job_id: uuid.UUID) -> dict[str, object]: ...

    def get_status(self, job_id: uuid.UUID) -> str: ...

    def advance(self, job_id: uuid.UUID, payload_updates: dict[str, object]) -> None: ...

    def complete(self, job_id: uuid.UUID) -> None: ...

    def fail(self, job_id: uuid.UUID, error: str) -> None:
        """`error` lands in `payload["errors"]` verbatim (see both
        implementations below). This table is internal-only today, but
        `TASK-033`'s future `GET /v1/ingest/{document_id}` route reads
        from it -- whoever wires that route must redact this field
        before it crosses that HTTP boundary (coding-standards.md's
        error-handling rule against leaking internal detail across a
        trust boundary; not yet a live violation since no such boundary
        exists in this diff, code-review finding, 2026-07-15)."""
        ...


class SqlAlchemyJobStore:
    """Real implementation against the `job_queue` table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_job(self, job_type: str) -> uuid.UUID:
        job = JobQueue(
            job_id=uuid.uuid4(), job_type=job_type, payload=dict(_INITIAL_PAYLOAD), status="pending"
        )
        self._session.add(job)
        self._session.flush()
        return job.job_id

    def get_payload(self, job_id: uuid.UUID) -> dict[str, object]:
        return self._fetch(job_id).payload

    def get_status(self, job_id: uuid.UUID) -> str:
        return self._fetch(job_id).status

    def advance(self, job_id: uuid.UUID, payload_updates: dict[str, object]) -> None:
        job = self._fetch(job_id)
        job.payload = {**job.payload, **payload_updates}
        job.status = "in_progress"

    def complete(self, job_id: uuid.UUID) -> None:
        job = self._fetch(job_id)
        job.payload = {**job.payload, "phase": "ready", "progress": 1.0}
        job.status = "complete"

    def fail(self, job_id: uuid.UUID, error: str) -> None:
        job = self._fetch(job_id)
        job.payload = {**job.payload, "phase": "failed", "errors": [error]}
        job.status = "failed"

    def _fetch(self, job_id: uuid.UUID) -> JobQueue:
        job = self._session.get(JobQueue, job_id)
        if job is None:
            raise LookupError(f"No job_queue row for {job_id}")
        return job


class InMemoryJobStore:
    """In-memory fake for tests."""

    def __init__(self) -> None:
        self._payloads: dict[uuid.UUID, dict[str, object]] = {}
        self._statuses: dict[uuid.UUID, str] = {}
        self._job_types: dict[uuid.UUID, str] = {}

    def create_job(self, job_type: str) -> uuid.UUID:
        job_id = uuid.uuid4()
        self._payloads[job_id] = dict(_INITIAL_PAYLOAD)
        self._statuses[job_id] = "pending"
        self._job_types[job_id] = job_type
        return job_id

    def get_payload(self, job_id: uuid.UUID) -> dict[str, object]:
        return dict(self._payloads[job_id])

    def get_status(self, job_id: uuid.UUID) -> str:
        return self._statuses[job_id]

    def advance(self, job_id: uuid.UUID, payload_updates: dict[str, object]) -> None:
        self._payloads[job_id] = {**self._payloads[job_id], **payload_updates}
        self._statuses[job_id] = "in_progress"

    def complete(self, job_id: uuid.UUID) -> None:
        self._payloads[job_id] = {**self._payloads[job_id], "phase": "ready", "progress": 1.0}
        self._statuses[job_id] = "complete"

    def fail(self, job_id: uuid.UUID, error: str) -> None:
        self._payloads[job_id] = {**self._payloads[job_id], "phase": "failed", "errors": [error]}
        self._statuses[job_id] = "failed"
