"""`POST /v1/ingest` + `GET /v1/ingest/{document_id}` (TASK-033 Issue 02) --
wires `ingest/pipeline.py`'s already-built, fully-tested pipeline to HTTP for
the first time.

**`document_id` == `job_id`, by design.** `ingest/job_store.py`'s
`JobStore.create_job()` generates its own `job_id`, independent of any
document identity a caller supplies -- there is no way to force it to equal
a separately-generated `document_id` without changing that already-tested
module. Rather than inventing a second id-mapping layer, this route creates
the job first and uses that same id as `documents.document_id` and
`DocumentIdentity.document_id` too, then calls `resume_ingest_job()` (which
takes an already-created `job_id`, unlike `ingest_document()`, which creates
its own) against the pre-created job. One id, one meaning, no mapping table.

**ACL bootstrap, resolved with the user, 2026-07-15**: `acl/ingest_stub.py`'s
`SqlAlchemyACLLookup` reads an existing `document_versions` row -- but a
brand-new upload has no such row yet. No real ECM integration exists yet
(`TASK-013`, Phase 3) to source Layer 1 ACL data from, so this route requires
the multipart form's `acl_override` field (present but marked "advanced" in
`specs/06-api-contracts.md`) and creates the `documents`/`document_versions`
rows from it directly -- rejecting with `400` if absent, matching this
codebase's fail-closed ACL philosophy (`acl/ingest_stub.py`'s own docstring)
rather than defaulting to an ACL of any kind.

**Error redaction**: `ingest/job_store.py`'s `JobStore.fail()` and
`ingest/pipeline.py`'s own exception handling store the *raw* exception text
in `job_queue.payload["errors"]` -- both modules' docstrings already flag
that whoever wires this HTTP route must redact it before it crosses the
trust boundary (`docs/coding-standards.md`'s error-handling rule; code
review, 2026-07-15, on both `JobStore.fail()` and `DocumentDecodeError`).
This route returns a generic message instead of the raw payload for a
`failed` job.

**Known gap, code review 2026-07-15, decided with the user**: `06-api-contracts.md`
documents this route's JWT auth as "(admin scope)" and lists `403` for an
insufficiently-scoped token, but `api/auth.py`'s `AuthContext` (Issue 01) has
no scope/role concept at all -- any correctly-signed JWT is accepted, `403`
is never returned. Left unresolved for now: this codebase has no end-user
JWT issuance flow yet (no login, no OIDC integration beyond JWKS signature
verification), so there is currently no way to obtain a "non-admin" JWT to
exploit this with -- the gap is real but unreachable in this phase. Must be
closed before any real end-user JWT issuance exists (Phase 3+); revisit then,
don't assume this note alone is sufficient once that changes.

**`corpus_id` = `repository_id`, formalized in specs 2026-07-16 (DEC-144)**:
`resolve_index_target(..., corpus_id=repository_id)` uses the request's
`repository_id` as the Qdrant `corpus_id` for collection naming. Originally
flagged (code review 2026-07-15) as an undefined relationship no spec file
stated explicitly; `update-specs` closed the gap by defining `corpus_id` as
formally equal to `documents.repository_id` for the single-collection-per-
repository MVP (`specs/13-decision-log.md` DEC-144, propagated into
`specs/04-architecture.md`, `specs/05-data-model.md`, `specs/07-database.md`).
This code already matched that definition; only the spec side needed to
catch up.

**Background-task session independence, peer review 2026-07-16**: an
external peer review flagged that `post_ingest`'s background task
(`_run_ingest_pipeline`) captured `deps`, whose `SqlAlchemyJobStore`/
`SqlAlchemyACLLookup` shared the request's own `Depends(get_session)`
session -- claiming that session gets closed before the background task
runs, crashing every job at `pending`. That specific mechanism doesn't hold
for this project's pinned `fastapi==0.135.2`/`starlette==1.0.0` (verified by
reading `fastapi/routing.py`'s `request_stack`/`function_stack` nesting and
`fastapi/dependencies/utils.py`'s `use_astack = request_astack` default, plus
a live repro): `BackgroundTasks` runs *before* an ordinary `yield`-dependency
without `scope="function"` tears down, not after. But sharing the session was
still wrong, for a different reason: the whole pipeline run -- job creation
through every phase transition -- rode on one transaction that would only
commit once `get_session()`'s post-yield code ran, which per the same ordering
is *after* the background task finishes. A concurrent `GET
/v1/ingest/{document_id}` poll (a separate request, separate session) would
see nothing but `404` for the entire run, and a hard process crash mid-run
would commit nothing at all -- not even the initial `pending` job row, worse
than Issue 02's own "left stuck at its last checkpoint" framing assumed (that
framing is still directionally right about crash recovery being unimplemented
-- `TASK-010`'s job, not this fix's -- just wrong about there being a
checkpoint to be stuck at). Fixed: the background task now gets its own
session from `get_background_pipeline_deps_factory`, opened and committed/
closed independently of the request's session; `post_ingest` commits its own
session explicitly, synchronously, right after creating the job/document/
version rows and before scheduling, so that independent session can actually
see them. This also removes the fix's own correctness from depending on
FastAPI's exact dependency-teardown-vs-background-task ordering at all --
it no longer matters which way that ordering goes.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Literal, NamedTuple

from fastapi import APIRouter, BackgroundTasks, Depends, Form, UploadFile
from pydantic import BaseModel, ValidationError
from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from acl.ingest_stub import SqlAlchemyACLLookup
from api.auth import AuthContext, require_auth
from api.schemas import ErrorResponse, error_response
from db.base import get_engine, get_session_factory
from ingest.embedding import HybridTEIEmbeddingClient, TEIDenseEmbeddingClient, TEISparseEmbeddingClient
from ingest.identity import DocumentIdentity
from ingest.job_store import JobPhase, JobStore, SqlAlchemyJobStore
from ingest.models import Document, DocumentVersion
from ingest.parsing import SUPPORTED_EXTENSIONS
from ingest.pipeline import PipelineDependencies, resume_ingest_job
from ingest.qdrant_setup import resolve_index_target
from ingest.task_scheduler import BackgroundTasksScheduler, TaskScheduler
from ingest.tokenizer import BgeM3Tokenizer

logger = logging.getLogger(__name__)

router = APIRouter()

# Single source of truth for "what's supported": derived from
# ingest/parsing.py's real SUPPORTED_EXTENSIONS, not an independently
# maintained MIME-type list that can drift (risk-review finding). Keys are
# what UploadFile.content_type reports for these formats.
_EXTENSION_TO_MIME_TYPE = {
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
assert set(_EXTENSION_TO_MIME_TYPE) == set(SUPPORTED_EXTENSIONS), (
    "SUPPORTED_EXTENSIONS changed in ingest/parsing.py without updating this mapping"
)
SUPPORTED_MIME_TYPES = frozenset(_EXTENSION_TO_MIME_TYPE.values())

ApiStatus = Literal["pending", "parsing", "indexing", "ready", "failed"]

_GENERIC_FAILURE_MESSAGE = "Ingest failed. Contact support with this document_id for details."


class ACLOverride(BaseModel):
    """Multipart form fields don't nest, so `acl_override` travels as a
    JSON-encoded string; this validates its shape once it's parsed."""

    allow_principals: list[str]
    deny_principals: list[str] = []
    security_label: str
    retention_state: str = "active"


class IngestResponse(BaseModel):
    document_id: str
    status_url: str


class IngestStatusResponse(BaseModel):
    status: ApiStatus
    progress: float
    errors: list[str]


def _map_phase_to_status(phase: JobPhase) -> ApiStatus:
    """`pending→pending`, `parsed→parsing`, `chunked→parsing`,
    `indexing→indexing`, `ready→ready`, `failed→failed` (both pre-indexing
    phases collapse into the one `parsing` bucket, matching
    `06-api-contracts.md`'s own worked poll-sequence example). No wildcard
    `case _` -- `JobPhase` is a closed `Literal`, so mypy flags this match
    as non-exhaustive if a case goes missing, catching drift at type-check
    time; the runtime `raise` below is defense-in-depth only, for if the
    `Literal` is ever widened without this match being updated to match."""
    match phase:
        case "pending":
            return "pending"
        case "parsed" | "chunked":
            return "parsing"
        case "indexing":
            return "indexing"
        case "ready":
            return "ready"
        case "failed":
            return "failed"
    raise ValueError(f"Unmapped JobPhase: {phase!r}")  # pragma: no cover


def get_session() -> Iterator[Session]:
    """Real per-request Postgres session. Tests override `get_job_store`/
    `get_background_pipeline_deps_factory` wholesale instead of this -- no
    live Postgres in this sandbox (`docs/agents/dev-environment.md`)."""
    factory = get_session_factory(get_engine())
    session = factory()
    try:
        yield session
        session.commit()
    finally:
        session.close()


def get_task_scheduler(background_tasks: BackgroundTasks) -> TaskScheduler:
    return BackgroundTasksScheduler(background_tasks)


def get_job_store(session: Session = Depends(get_session)) -> JobStore:
    """Narrower than `get_pipeline_dependencies` -- both routes below only
    ever touch `.job_store`, never the tokenizer/embedding/Qdrant clients
    `PipelineDependencies` also bundles. Building those on every request,
    including a bare `GET /v1/ingest/{document_id}` status poll, was real,
    avoidable waste (`BgeM3Tokenizer()` alone makes a HuggingFace Hub call)
    -- Spec-axis code review, 2026-07-16."""
    return SqlAlchemyJobStore(session)


def _build_pipeline_clients() -> tuple[BgeM3Tokenizer, HybridTEIEmbeddingClient, QdrantClient]:
    """Session-independent pieces of `PipelineDependencies`, built once per
    `get_background_pipeline_deps_factory` instantiation -- env-var driven
    (matching `db/base.py`'s `DATABASE_URL` pattern). Not exercised by any
    automated test in this sandbox -- round-tripping this against real
    Postgres/Qdrant/TEI is `[manual-verify]`, same ceiling as every other
    real-service integration in this codebase."""
    tei_dense_url = os.environ.get("TEI_DENSE_URL")
    tei_sparse_url = os.environ.get("TEI_SPARSE_URL")
    qdrant_url = os.environ.get("QDRANT_URL")
    if not (tei_dense_url and tei_sparse_url and qdrant_url):
        raise RuntimeError(
            "TEI_DENSE_URL, TEI_SPARSE_URL, and QDRANT_URL must all be set to build "
            "production ingest pipeline dependencies"
        )
    return (
        BgeM3Tokenizer(),
        HybridTEIEmbeddingClient(
            TEIDenseEmbeddingClient(tei_dense_url), TEISparseEmbeddingClient(tei_sparse_url)
        ),
        QdrantClient(url=qdrant_url),
    )


class BackgroundPipelineDeps(NamedTuple):
    """A `PipelineDependencies` paired with the session it's bound to, so a
    caller can commit/close that exact session once the pipeline run is done
    -- named fields instead of a positional tuple, since `deps`/`session`
    travel together at every call site that uses
    `get_background_pipeline_deps_factory` (Standards-axis code review,
    2026-07-16)."""

    deps: PipelineDependencies
    session: Session


def get_background_pipeline_deps_factory() -> Callable[[], BackgroundPipelineDeps]:
    """Returns a *factory*, not a `PipelineDependencies` itself. Each call to
    the returned callable opens a brand-new session (via `db/base.py`'s own
    `get_session_factory(get_engine())` pattern) and binds a fresh
    `SqlAlchemyJobStore`/`SqlAlchemyACLLookup` to it -- deliberately not the
    request's own `Depends(get_session)` session (see this module's own
    docstring on why sharing it was wrong). The caller owns the returned
    session's commit/close. Session-independent clients (tokenizer/embedding/
    Qdrant) are built once per factory instantiation and safely reused across
    calls, since they hold no per-request state."""
    tokenizer, embedding_client, qdrant_client = _build_pipeline_clients()
    session_factory = get_session_factory(get_engine())

    def _build() -> BackgroundPipelineDeps:
        session = session_factory()
        deps = PipelineDependencies(
            tokenizer=tokenizer,
            job_store=SqlAlchemyJobStore(session),
            acl_lookup=SqlAlchemyACLLookup(session),
            embedding_client=embedding_client,
            qdrant_client=qdrant_client,
        )
        return BackgroundPipelineDeps(deps=deps, session=session)

    return _build


def _create_document_and_version(
    session: Session, *, document_id: uuid.UUID, repository_id: str, acl: ACLOverride
) -> str:
    """Creates the `documents` + `document_versions` rows a brand-new upload
    needs before ingest can run (see this module's own docstring on the ACL
    bootstrap this exists for). Returns the new `version_id`."""
    now = datetime.now(UTC)
    version_id = str(uuid.uuid4())
    session.add(
        Document(document_id=document_id, repository_id=repository_id, created_at=now, updated_at=now)
    )
    session.add(
        DocumentVersion(
            document_id=document_id,
            version_id=version_id,
            # True, not the column default -- this is a direct upload, not
            # an in-flight ECM checkout (DEC-071's "uncommitted" state
            # describes an ECM checkout workflow this route doesn't have).
            is_committed=True,
            security_label=acl.security_label,
            retention_state=acl.retention_state,
            allow_principals=acl.allow_principals,
            deny_principals=acl.deny_principals,
            ingested_at=now,
        )
    )
    return version_id


@router.post(
    "/v1/ingest",
    response_model=IngestResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Missing or invalid acl_override"},
        401: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        415: {"model": ErrorResponse, "description": "Unsupported upload format"},
    },
)
async def post_ingest(
    file: UploadFile,
    repository_id: str = Form(default="default"),
    acl_override: str | None = Form(default=None),
    auth: AuthContext = Depends(require_auth),
    scheduler: TaskScheduler = Depends(get_task_scheduler),
    job_store: JobStore = Depends(get_job_store),
    session: Session = Depends(get_session),
    background_pipeline_deps_factory: Callable[[], BackgroundPipelineDeps] = Depends(
        get_background_pipeline_deps_factory
    ),
) -> IngestResponse | object:
    if file.content_type not in SUPPORTED_MIME_TYPES:
        return error_response(
            415,
            "unsupported_media_type",
            f"Unsupported upload format: {file.content_type!r}",
            details={"supported_formats": sorted(SUPPORTED_MIME_TYPES)},
        )

    if acl_override is None:
        return error_response(
            400, "invalid_request", "acl_override is required (no ECM integration in this phase)"
        )
    try:
        acl = ACLOverride.model_validate(json.loads(acl_override))
    except (json.JSONDecodeError, ValidationError) as exc:
        return error_response(400, "invalid_request", f"Invalid acl_override: {exc}")

    job_id = job_store.create_job("ingest")
    version_id = _create_document_and_version(
        session, document_id=job_id, repository_id=repository_id, acl=acl
    )
    # Commit now, synchronously -- the background task below opens its own,
    # independent session (get_background_pipeline_deps_factory; see this
    # module's own docstring) and needs the job/document/version rows to
    # already be durable and visible to it, not just pending in this session.
    # get_session()'s own post-yield `session.commit()` still runs too, once
    # this request's dependency teardown eventually happens -- a harmless
    # no-op second commit on a session with nothing left uncommitted, not a
    # double-write, so it's left as-is rather than restructured to avoid it.
    session.commit()

    identity = DocumentIdentity(document_id=job_id, version_id=version_id, repository_id=repository_id)
    target = resolve_index_target(session, corpus_id=repository_id)
    file_bytes = await file.read()
    filename = file.filename or "upload"

    def _run_ingest_pipeline() -> None:
        background = background_pipeline_deps_factory()
        try:
            try:
                resume_ingest_job(
                    job_id, file_bytes, filename, identity=identity, target=target, deps=background.deps
                )
            finally:
                # Commit regardless of outcome: on failure, ingest/pipeline.py's
                # own _run_pipeline() already wrote a "failed" job_store update
                # before re-raising -- that update must persist too, not just
                # a successful run's "ready" state.
                background.session.commit()
        finally:
            background.session.close()

    scheduler.schedule(_run_ingest_pipeline)
    logger.warning(
        "job %s scheduled for background processing; crash recovery not implemented until TASK-010",
        job_id,
    )

    return IngestResponse(document_id=str(job_id), status_url=f"/v1/ingest/{job_id}")


@router.get(
    "/v1/ingest/{document_id}",
    response_model=IngestStatusResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        404: {"model": ErrorResponse, "description": "Unknown document_id"},
    },
)
async def get_ingest_status(
    document_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    job_store: JobStore = Depends(get_job_store),
) -> IngestStatusResponse | object:
    try:
        payload = job_store.get_payload(document_id)
    except LookupError:
        # Covers both InMemoryJobStore's bare KeyError (a subclass of
        # LookupError) and SqlAlchemyJobStore's own explicit LookupError.
        return error_response(404, "not_found", f"No ingest job for document_id {document_id}")

    phase: JobPhase = payload.get("phase", "pending")  # type: ignore[assignment]
    status = _map_phase_to_status(phase)
    errors = [_GENERIC_FAILURE_MESSAGE] if status == "failed" else []
    progress = payload.get("progress", 0.0)
    assert isinstance(progress, (int, float)), f"job_queue.payload['progress'] was {type(progress)!r}, not numeric"
    return IngestStatusResponse(status=status, progress=float(progress), errors=errors)
