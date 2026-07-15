"""bge-m3 dense embedding + dedicated-SPLADE-model sparse embedding,
both via TEI, in separate deployments (DEC-142, 2026-07-15).

**Dense**: `TEIDenseEmbeddingClient` calls bge-m3's TEI deployment's
`POST /embed` -- confirmed working (TEI serves bge-m3 as a regular
XLM-RoBERTa model; community confirmation, TEI GitHub issue #141:
`/info` + a live encoding call against a real `BAAI/bge-m3` deployment).

**Sparse**: `TEISparseEmbeddingClient` calls a *separate* TEI
deployment's `POST /embed_sparse`, running a dedicated SPLADE-
architecture model (`--pooling splade`, MaskedLM-only per TEI's own
README) -- **not** bge-m3. bge-m3's own sparse output is not servable
through TEI at all: its sparse mechanism needs a linear head applied to
the model's raw, unpooled `last_hidden_state`, which TEI's serving
architecture does not expose for any model (same root cause as
bge-m3's ColBERT output also not being exposed -- confirmed via TEI's
GitHub issue #141's full comment thread, corrected 2026-07-13 cross-
model review's own R.26 finding, which had caught the ColBERT half of
this gap but not the sparse half).

`HybridTEIEmbeddingClient` composes both into the full `EmbeddingClient`
Protocol. See `specs/13-decision-log.md` DEC-142 for the full rationale,
the two alternatives considered (running BAAI's own `FlagEmbedding`
library directly; dropping sparse retrieval), and the accepted trade-offs
(dense/sparse from two independently-trained models instead of one
jointly-trained model; two embedding calls per text instead of one, at
both ingest and query time; an unquantified VRAM-budget addition).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from ingest.qdrant_setup import DENSE_VECTOR_SIZE


@dataclass(frozen=True)
class EmbeddingResult:
    dense: list[float]
    sparse_indices: list[int]
    sparse_values: list[float]


@dataclass(frozen=True)
class SparseEmbedding:
    indices: list[int]
    values: list[float]


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[EmbeddingResult]: ...


class TEIDenseEmbeddingClient:
    """Real client for bge-m3's dense embedding, via its own TEI
    deployment's `POST /embed`."""

    def __init__(self, base_url: str, http_client: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = http_client or httpx.Client()

    def embed_dense(self, texts: list[str]) -> list[list[float]]:
        response = self._http.post(f"{self._base_url}/embed", json={"inputs": texts})
        response.raise_for_status()
        result: list[list[float]] = response.json()
        return result


class TEISparseEmbeddingClient:
    """Real client for a dedicated SPLADE model's sparse embedding, via
    its own, separate TEI deployment's `POST /embed_sparse`.

    Response shape verified against TEI's own Rust source
    (`router/src/http/types.rs`): `EmbedSparseResponse(Vec<Vec<SparseValue>>)`
    where `SparseValue = {index: usize, value: f32}` -- one list of
    `{index, value}` pairs per input text.
    """

    def __init__(self, base_url: str, http_client: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = http_client or httpx.Client()

    def embed_sparse(self, texts: list[str]) -> list[SparseEmbedding]:
        response = self._http.post(f"{self._base_url}/embed_sparse", json={"inputs": texts})
        response.raise_for_status()
        raw: list[list[dict[str, float]]] = response.json()
        return [
            SparseEmbedding(
                indices=[int(entry["index"]) for entry in per_text],
                values=[float(entry["value"]) for entry in per_text],
            )
            for per_text in raw
        ]


class HybridTEIEmbeddingClient:
    """Composes a dense client and a sparse client (two separate TEI
    deployments) into the full `EmbeddingClient` Protocol.

    **Known trade-off, not fixed** (external peer review, 2026-07-15,
    `.scratch/review-reports/document-ingest-pipeline-issue01-02-peer-review.md`
    P.1, LOW): `embed()` calls dense then sparse sequentially. Callers that
    retry the whole `embed()` call on failure (`ingest/pipeline.py::_embed_with_retry`)
    will redundantly recompute dense on every retry triggered by a
    sparse-only outage, since this method has no memory of a prior
    partial success. Bounded by the caller's own retry cap (currently
    `MAX_EMBEDDING_RETRY_ATTEMPTS=5`) and considered a genuine edge case
    (both TEI deployments likely share infrastructure) rather than a
    common-path cost -- a real fix (independent dense/sparse retry) would
    need this class to own backoff/job-store-visibility concerns that
    `ingest/pipeline.py` currently owns instead, which is a bigger
    boundary change than this LOW-severity finding justifies on its own.
    """

    def __init__(self, dense_client: TEIDenseEmbeddingClient, sparse_client: TEISparseEmbeddingClient) -> None:
        self._dense_client = dense_client
        self._sparse_client = sparse_client

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        dense_vectors = self._dense_client.embed_dense(texts)
        sparse_embeddings = self._sparse_client.embed_sparse(texts)
        if len(dense_vectors) != len(sparse_embeddings):
            raise ValueError(
                f"Dense ({len(dense_vectors)}) and sparse ({len(sparse_embeddings)}) "
                "result counts disagree -- the two TEI deployments returned a "
                "different number of results for the same input batch."
            )
        return [
            EmbeddingResult(dense=dense, sparse_indices=sparse.indices, sparse_values=sparse.values)
            for dense, sparse in zip(dense_vectors, sparse_embeddings, strict=True)
        ]


class FakeEmbeddingClient:
    """Deterministic, offline stand-in for pipeline-orchestration tests
    -- returns a fixed-shape dense+sparse pair per input text,
    independent of which real models/deployments back the hybrid client
    above (this fake exists to test the pipeline's own wiring, not to
    model either TEI deployment's actual behavior)."""

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        return [
            EmbeddingResult(
                dense=[float(len(text) % 7 + 1)] * DENSE_VECTOR_SIZE,
                sparse_indices=[0, 1],
                sparse_values=[0.5, 0.5],
            )
            for text in texts
        ]
