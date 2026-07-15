"""Tests for ingest/embedding.py.

Split dense/sparse design (DEC-142, 2026-07-15): bge-m3's own sparse
output is not servable through TEI (confirmed via TEI's own GitHub
issue #141) -- dense comes from bge-m3's TEI deployment
(`TEIDenseEmbeddingClient`), sparse comes from a separate, dedicated
SPLADE model's TEI deployment (`TEISparseEmbeddingClient`), composed
into the full `EmbeddingClient` Protocol by `HybridTEIEmbeddingClient`.
Both real clients are exercised here via `httpx.MockTransport` -- no
live TEI server needed.
"""

from __future__ import annotations

import json

import httpx
import pytest

from ingest.embedding import (
    EmbeddingResult,
    FakeEmbeddingClient,
    HybridTEIEmbeddingClient,
    SparseEmbedding,
    TEIDenseEmbeddingClient,
    TEISparseEmbeddingClient,
)


def test_fake_embedding_client_returns_one_result_per_input_text() -> None:
    client = FakeEmbeddingClient()
    results = client.embed(["hello world", "a second chunk of text"])
    assert len(results) == 2
    for result in results:
        assert isinstance(result, EmbeddingResult)
        assert len(result.dense) > 0
        assert len(result.sparse_indices) == len(result.sparse_values)


def test_fake_embedding_client_is_deterministic() -> None:
    client = FakeEmbeddingClient()
    assert client.embed(["same text"]) == client.embed(["same text"])


# --- TEIDenseEmbeddingClient (bge-m3, confirmed-working via TEI /embed) ----


def test_dense_client_sends_expected_request_and_parses_response() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TEIDenseEmbeddingClient(base_url="http://tei-dense.local:8080", http_client=http_client)

    result = client.embed_dense(["first chunk", "second chunk"])

    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert len(captured_requests) == 1
    assert captured_requests[0].url.path == "/embed"


def test_dense_client_request_body_matches_tei_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        body = json.loads(request.content)
        assert body == {"inputs": ["only chunk"]}
        return httpx.Response(200, json=[[1.0]])

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TEIDenseEmbeddingClient(base_url="http://tei-dense.local:8080", http_client=http_client)

    client.embed_dense(["only chunk"])


def test_dense_client_raises_on_non_2xx_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "internal"})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TEIDenseEmbeddingClient(base_url="http://tei-dense.local:8080", http_client=http_client)

    with pytest.raises(httpx.HTTPStatusError):
        client.embed_dense(["chunk"])


# --- TEISparseEmbeddingClient (dedicated SPLADE model, DEC-142) -----------


def test_sparse_client_sends_expected_request_and_parses_response() -> None:
    """Response shape verified against TEI's own Rust source
    (router/src/http/types.rs): EmbedSparseResponse(Vec<Vec<SparseValue>>)
    where SparseValue = {index: usize, value: f32} -- serializes as a
    JSON array per input text, each a list of {"index", "value"} objects.
    """
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json=[
                [{"index": 5, "value": 0.34}, {"index": 102, "value": 0.12}],
                [{"index": 8, "value": 0.51}],
            ],
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TEISparseEmbeddingClient(base_url="http://tei-sparse.local:8081", http_client=http_client)

    result = client.embed_sparse(["first chunk", "second chunk"])

    assert result == [
        SparseEmbedding(indices=[5, 102], values=[0.34, 0.12]),
        SparseEmbedding(indices=[8], values=[0.51]),
    ]
    assert len(captured_requests) == 1
    assert captured_requests[0].url.path == "/embed_sparse"


def test_sparse_client_request_body_matches_tei_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        body = json.loads(request.content)
        assert body == {"inputs": ["only chunk"]}
        return httpx.Response(200, json=[[{"index": 0, "value": 1.0}]])

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TEISparseEmbeddingClient(base_url="http://tei-sparse.local:8081", http_client=http_client)

    client.embed_sparse(["only chunk"])


def test_sparse_client_handles_a_text_with_no_nonzero_sparse_entries() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[[]])

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TEISparseEmbeddingClient(base_url="http://tei-sparse.local:8081", http_client=http_client)

    result = client.embed_sparse(["text"])
    assert result == [SparseEmbedding(indices=[], values=[])]


def test_sparse_client_raises_on_non_2xx_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(424, json={"error": "model is not SPLADE-pooled"})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TEISparseEmbeddingClient(base_url="http://tei-sparse.local:8081", http_client=http_client)

    with pytest.raises(httpx.HTTPStatusError):
        client.embed_sparse(["chunk"])


# --- HybridTEIEmbeddingClient (composes both into EmbeddingClient) --------


def test_hybrid_client_combines_dense_and_sparse_results(mocker) -> None:  # type: ignore[no-untyped-def]
    dense_client = mocker.Mock(spec=TEIDenseEmbeddingClient)
    dense_client.embed_dense.return_value = [[0.1, 0.2], [0.3, 0.4]]
    sparse_client = mocker.Mock(spec=TEISparseEmbeddingClient)
    sparse_client.embed_sparse.return_value = [
        SparseEmbedding(indices=[1], values=[0.9]),
        SparseEmbedding(indices=[2, 3], values=[0.5, 0.6]),
    ]

    hybrid = HybridTEIEmbeddingClient(dense_client=dense_client, sparse_client=sparse_client)
    results = hybrid.embed(["a", "b"])

    assert results == [
        EmbeddingResult(dense=[0.1, 0.2], sparse_indices=[1], sparse_values=[0.9]),
        EmbeddingResult(dense=[0.3, 0.4], sparse_indices=[2, 3], sparse_values=[0.5, 0.6]),
    ]
    dense_client.embed_dense.assert_called_once_with(["a", "b"])
    sparse_client.embed_sparse.assert_called_once_with(["a", "b"])


def test_hybrid_client_raises_if_dense_and_sparse_counts_disagree(mocker) -> None:  # type: ignore[no-untyped-def]
    dense_client = mocker.Mock(spec=TEIDenseEmbeddingClient)
    dense_client.embed_dense.return_value = [[0.1, 0.2]]
    sparse_client = mocker.Mock(spec=TEISparseEmbeddingClient)
    sparse_client.embed_sparse.return_value = [
        SparseEmbedding(indices=[1], values=[0.9]),
        SparseEmbedding(indices=[2], values=[0.5]),
    ]

    hybrid = HybridTEIEmbeddingClient(dense_client=dense_client, sparse_client=sparse_client)
    with pytest.raises(ValueError, match="disagree"):
        hybrid.embed(["a"])
