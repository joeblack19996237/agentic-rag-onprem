"""Shared fixtures for tests/api/ (ingest-route-specific -- `client`/`keys`/
`admin_api_key`/`jwt_headers` live in tests/_shared_auth_fixtures.py, shared
with tests/admin/; see that module's docstring for why it isn't itself named
conftest.py). A real conftest.py, auto-discovered by pytest's own fixture
machinery -- never explicitly dotted-imported by any test module here, which
is what would recreate the collision `tests/ingest/pdf_docx_fixtures.py`'s
docstring warns about (pytest auto-importing conftest.py as a bare top-level
module while a dotted import elsewhere loads the same file under a second
module identity)."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from acl.ingest_stub import FakeACLLookup
from api.ingest_routes import (
    BackgroundPipelineDeps,
    get_background_pipeline_deps_factory,
    get_job_store,
    get_session,
    get_task_scheduler,
)
from api.main import app
from ingest.embedding import FakeEmbeddingClient
from ingest.job_store import InMemoryJobStore
from ingest.pipeline import PipelineDependencies
from ingest.task_scheduler import FakeTaskScheduler
from ingest.tokenizer import FakeTokenizer
from tests._shared_auth_fixtures import admin_api_key as admin_api_key
from tests._shared_auth_fixtures import client as client
from tests._shared_auth_fixtures import jwt_headers as jwt_headers
from tests._shared_auth_fixtures import keys as keys


@pytest.fixture
def job_store() -> InMemoryJobStore:
    return InMemoryJobStore()


@pytest.fixture
def mock_session() -> MagicMock:
    """A bare mock, not a real Session -- no live Postgres in this sandbox.
    `resolve_index_target()`'s `session.execute(...).scalar_one_or_none()`
    call needs a value; `session.add()` calls (Document/DocumentVersion
    creation) are asserted on via `call_args_list`, not given real
    persistence semantics."""
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "test-embedding-model-v1"
    return session


@pytest.fixture
def fake_pipeline_deps(job_store: InMemoryJobStore) -> PipelineDependencies:
    return PipelineDependencies(
        tokenizer=FakeTokenizer(),
        job_store=job_store,
        acl_lookup=FakeACLLookup(),
        embedding_client=FakeEmbeddingClient(),
        qdrant_client=QdrantClient(":memory:"),
    )


@pytest.fixture
def fake_scheduler() -> FakeTaskScheduler:
    return FakeTaskScheduler()


@pytest.fixture
def fake_background_pipeline_deps_factory(
    fake_pipeline_deps: PipelineDependencies,
) -> Callable[[], BackgroundPipelineDeps]:
    """Fakes `get_background_pipeline_deps_factory`'s return value: a
    zero-arg callable, not a `PipelineDependencies` itself (see the real
    dependency's own docstring on why the background task needs its own
    session). Reuses `fake_pipeline_deps` -- none of the route-level tests
    using the plain `ingest_client` fixture actually invoke the background
    closure (they all schedule via `fake_scheduler`, which records without
    running it), so this only needs to make dependency *resolution* safe.
    `test_ingest_routes.py`'s own dedicated session-independence test builds
    its own factory instead, to actually observe per-call behavior."""

    def _build() -> BackgroundPipelineDeps:
        return BackgroundPipelineDeps(deps=fake_pipeline_deps, session=MagicMock())

    return _build


@pytest.fixture
def ingest_client(
    client: TestClient,
    job_store: InMemoryJobStore,
    fake_scheduler: FakeTaskScheduler,
    mock_session: MagicMock,
    fake_background_pipeline_deps_factory: Callable[[], BackgroundPipelineDeps],
) -> Iterator[TestClient]:
    """`client` plus the ingest-route-specific dependency overrides. Cleans
    up `app.dependency_overrides` afterward so nothing leaks into a test
    module that doesn't use this fixture."""
    app.dependency_overrides[get_job_store] = lambda: job_store
    app.dependency_overrides[get_task_scheduler] = lambda: fake_scheduler
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_background_pipeline_deps_factory] = (
        lambda: fake_background_pipeline_deps_factory
    )
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_job_store, None)
        app.dependency_overrides.pop(get_task_scheduler, None)
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_background_pipeline_deps_factory, None)
