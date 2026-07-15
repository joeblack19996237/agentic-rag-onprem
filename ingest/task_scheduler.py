"""Scheduling seam for the ingest HTTP route (TASK-033 Issue 02). A minimal
`Protocol` + real adapter + fake, matching this module's own established
pattern (`JobStore`, `acl/ingest_stub.py`'s `ACLLookup`, `ingest/embedding.py`'s
`EmbeddingClient`) -- deliberately not a spy on FastAPI's `BackgroundTasks`
directly, which would test a third-party library's implementation detail
rather than this system's own scheduling behavior. `TASK-010` replaces
`BackgroundTasksScheduler` with a real Postgres job-queue dispatcher without
touching the calling code or its tests -- only the adapter changes.
"""

from __future__ import annotations

from typing import Callable, Protocol

from fastapi import BackgroundTasks


class TaskScheduler(Protocol):
    def schedule(self, fn: Callable[[], None]) -> None: ...


class BackgroundTasksScheduler:
    """Real adapter over FastAPI's in-process `BackgroundTasks`. Not crash-
    resilient -- if the process dies mid-job, the job is stuck at its last
    checkpoint until `TASK-010`'s dispatcher exists to re-poll it."""

    def __init__(self, background_tasks: BackgroundTasks) -> None:
        self._background_tasks = background_tasks

    def schedule(self, fn: Callable[[], None]) -> None:
        self._background_tasks.add_task(fn)


class FakeTaskScheduler:
    """Records scheduled callables without running them -- proves a call
    was scheduled (not awaited inline), without testing which specific
    third-party method did the scheduling."""

    def __init__(self) -> None:
        self.scheduled: list[Callable[[], None]] = []

    def schedule(self, fn: Callable[[], None]) -> None:
        self.scheduled.append(fn)
