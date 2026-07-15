"""Tests for ingest/embedding.py.

TEIEmbeddingClient.embed_dense() is TEI's confirmed-working half (real
POST /embed, exercised here via httpx.MockTransport -- no live TEI
server needed). TEIEmbeddingClient.embed() (the full dense+sparse
Protocol method) is expected to raise: bge-m3's sparse output is not
actually servable through TEI, confirmed via TEI's own GitHub issue #141
(open) during risk review, 2026-07-15 -- see ingest/embedding.py's
module docstring. This is a real, currently-unresolved architecture gap
(DEC-035/DEC-086/REQ-003), not a bug to silently work around here.
"""

from __future__ import annotations

import httpx
import pytest

from ingest.embedding import (
    EmbeddingResult,
    FakeEmbeddingClient,
    TeiEmbeddingUnsupportedSparseError,
    TEIEmbeddingClient,
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


def test_tei_client_embed_dense_sends_expected_request_and_parses_response() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TEIEmbeddingClient(base_url="http://tei.local:8080", http_client=http_client)

    result = client.embed_dense(["first chunk", "second chunk"])

    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert len(captured_requests) == 1
    assert captured_requests[0].url.path == "/embed"
    assert httpx.QueryParams(captured_requests[0].url.query) == httpx.QueryParams()


def test_tei_client_embed_dense_request_body_matches_tei_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        import json as _json

        body = _json.loads(request.content)
        assert body == {"inputs": ["only chunk"]}
        return httpx.Response(200, json=[[1.0]])

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TEIEmbeddingClient(base_url="http://tei.local:8080", http_client=http_client)

    client.embed_dense(["only chunk"])


def test_tei_client_embed_dense_raises_on_non_2xx_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "internal"})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TEIEmbeddingClient(base_url="http://tei.local:8080", http_client=http_client)

    with pytest.raises(httpx.HTTPStatusError):
        client.embed_dense(["chunk"])


def test_tei_client_full_embed_raises_unsupported_sparse_error() -> None:
    client = TEIEmbeddingClient(base_url="http://tei.local:8080")
    with pytest.raises(TeiEmbeddingUnsupportedSparseError):
        client.embed(["chunk"])
