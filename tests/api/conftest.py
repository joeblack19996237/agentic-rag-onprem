"""Shared fixtures for tests/api/. A real conftest.py, auto-discovered by
pytest's own fixture machinery -- never explicitly dotted-imported by any
test module here, which is what would recreate the collision
`tests/ingest/pdf_docx_fixtures.py`'s docstring warns about (pytest
auto-importing conftest.py as a bare top-level module while a dotted import
elsewhere loads the same file under a second module identity)."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any
from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm, OKPAlgorithm, RSAAlgorithm
from qdrant_client import QdrantClient

from acl.ingest_stub import FakeACLLookup
from api.ingest_routes import get_pipeline_dependencies, get_session, get_task_scheduler
from api.main import app
from ingest.embedding import FakeEmbeddingClient
from ingest.job_store import InMemoryJobStore
from ingest.pipeline import PipelineDependencies
from ingest.task_scheduler import FakeTaskScheduler
from ingest.tokenizer import FakeTokenizer


@pytest.fixture
def admin_api_key() -> str:
    return "test-admin-key-do-not-use-in-prod"  # noqa: S105 -- test fixture value, not a real secret


@pytest.fixture(scope="module")
def keys() -> dict[str, Any]:
    return {
        "rsa": rsa.generate_private_key(public_exponent=65537, key_size=2048),
        "ec": ec.generate_private_key(ec.SECP256R1()),
        "ed": ed25519.Ed25519PrivateKey.generate(),
    }


@pytest.fixture
def client(keys: dict[str, Any], admin_api_key: str) -> TestClient:
    bundle = {
        "keys": [
            json.loads(RSAAlgorithm.to_jwk(keys["rsa"].public_key())) | {"kid": "rsa-1", "use": "sig"},
            json.loads(ECAlgorithm.to_jwk(keys["ec"].public_key())) | {"kid": "ec-1", "use": "sig"},
            json.loads(OKPAlgorithm.to_jwk(keys["ed"].public_key())) | {"kid": "ed-1", "use": "sig"},
        ]
    }
    app.state.jwks = jwt.PyJWKSet.from_dict(bundle)
    app.state.admin_api_key = admin_api_key
    return TestClient(app)


@pytest.fixture
def jwt_headers(keys: dict[str, Any]) -> Callable[[], dict[str, str]]:
    """A quick "just give me a valid, accepted credential" builder for tests
    that don't care about JWT algorithm/kid specifics (those live in
    test_auth.py) and just need a route to authenticate successfully."""

    def _build() -> dict[str, str]:
        token = jwt.encode({"sub": "user-1"}, keys["rsa"], algorithm="RS256", headers={"kid": "rsa-1"})
        return {"Authorization": f"Bearer {token}"}

    return _build


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
def ingest_client(
    client: TestClient,
    fake_pipeline_deps: PipelineDependencies,
    fake_scheduler: FakeTaskScheduler,
    mock_session: MagicMock,
) -> Iterator[TestClient]:
    """`client` plus the ingest-route-specific dependency overrides. Cleans
    up `app.dependency_overrides` afterward so nothing leaks into a test
    module that doesn't use this fixture."""
    app.dependency_overrides[get_pipeline_dependencies] = lambda: fake_pipeline_deps
    app.dependency_overrides[get_task_scheduler] = lambda: fake_scheduler
    app.dependency_overrides[get_session] = lambda: mock_session
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_pipeline_dependencies, None)
        app.dependency_overrides.pop(get_task_scheduler, None)
        app.dependency_overrides.pop(get_session, None)
