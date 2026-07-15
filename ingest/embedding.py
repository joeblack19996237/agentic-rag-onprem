"""bge-m3 embedding via TEI -- dense confirmed working, sparse unresolved.

**Dense** embedding via TEI's `POST /embed` is confirmed working for
bge-m3 -- TEI serves it as a regular XLM-RoBERTa model (community
confirmation: TEI GitHub issue #141, `/info` + a live encoding call
against a real `BAAI/bge-m3` deployment).

**Sparse** embedding is NOT confirmed working through TEI. TEI's
`/embed_sparse` endpoint is built for SPLADE-architecture models
(requires `--pooling splade`, MaskedLM-only per TEI's own README);
bge-m3's own sparse mechanism needs a different linear head applied to
the model's raw, unpooled `last_hidden_state`, which TEI does not
expose. Direct quote from a knowledgeable contributor on TEI's own
GitHub issue #141 (open as of 2026-07-15): "there's no way to use the
sparse or colbert features of this model... no way to get TEI to give
back the last_hidden_state."

This is a real gap in this project's existing architecture
(`specs/13-decision-log.md` DEC-035 -- TEI serves embedding; DEC-086/
REQ-003 -- bge-m3 chosen specifically for one-call dense+sparse hybrid
retrieval), found during `data-foundation`/`document-ingest-pipeline`
risk review, 2026-07-15. It is not resolved here -- `TEIEmbeddingClient`
is honest about it (raises rather than silently returning a fabricated
or dense-only "sparse" vector) rather than working around it quietly.
Needs a `DEC-###` entry and a real decision (e.g. serving bge-m3's
sparse side via BAAI's own `FlagEmbedding` library directly, not
through TEI) before ingest can be wired to a live embedding service.
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


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[EmbeddingResult]: ...


class TeiEmbeddingUnsupportedSparseError(NotImplementedError):
    """Raised because bge-m3 sparse embedding via TEI is unresolved --
    see this module's docstring. Not a bug to fix locally; needs an
    architecture decision first."""


class TEIEmbeddingClient:
    """Real client. `embed_dense` is the confirmed-working half.
    `embed` (the full `EmbeddingClient` Protocol method, dense+sparse)
    raises rather than fabricate a sparse vector TEI cannot produce."""

    def __init__(self, base_url: str, http_client: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = http_client or httpx.Client()

    def embed_dense(self, texts: list[str]) -> list[list[float]]:
        response = self._http.post(f"{self._base_url}/embed", json={"inputs": texts})
        response.raise_for_status()
        result: list[list[float]] = response.json()
        return result

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        raise TeiEmbeddingUnsupportedSparseError(
            "bge-m3 sparse embedding via TEI is unresolved (TEI GitHub issue #141) -- "
            "needs an architecture decision before this client can serve real ingest."
        )


class FakeEmbeddingClient:
    """Deterministic, offline stand-in for pipeline-orchestration tests
    -- returns a fixed-shape dense+sparse pair per input text,
    independent of the real TEI/bge-m3 sparse-support gap above (this
    fake exists to test the pipeline's own wiring, not to model TEI's
    actual capabilities)."""

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        return [
            EmbeddingResult(
                dense=[float(len(text) % 7 + 1)] * DENSE_VECTOR_SIZE,
                sparse_indices=[0, 1],
                sparse_values=[0.5, 0.5],
            )
            for text in texts
        ]
