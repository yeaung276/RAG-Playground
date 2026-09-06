"""Behaviour of the semantic chunker's embeddings adapter: /embed request shape,
batching at TEI_MAX_BATCH, vector ordering, retry policy, and rate limiting. Calls
are made from a worker thread, as IndexingService drives the chunker."""

import asyncio
import json
import time

import httpx
import pytest
from aiolimiter import AsyncLimiter

from app.services.retrieval.chunking.semantic import TEI_MAX_BATCH, _TEIEmbeddings
from app.services.retrieval.embedding import tei


@pytest.fixture(autouse=True)
def tei_env(monkeypatch):
    monkeypatch.setenv("TEI_EMBEDDING_BASE_URL", "http://tei.test/")
    monkeypatch.setenv("TEI_EMBEDDING_API_KEY", "secret")


def _stub(embeddings: _TEIEmbeddings, handler) -> _TEIEmbeddings:
    """Point the embedder at a MockTransport, keeping the headers it was built with."""
    client = embeddings._embedder.client
    embeddings._embedder.client = httpx.AsyncClient(
        headers=client.headers, transport=httpx.MockTransport(handler)
    )
    return embeddings


def _inputs(request: httpx.Request) -> list[str]:
    return json.loads(request.content)["inputs"]


def _echo_index(request: httpx.Request) -> httpx.Response:
    """Vector [i] for text "t{i}", so a reordered response shows up in the result."""
    return httpx.Response(200, json=[[float(t[1:])] for t in _inputs(request)])


async def test_posts_inputs_to_the_embed_route():
    seen: list[httpx.Request] = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=[[1.0, 0.0]])

    embeddings = _stub(_TEIEmbeddings(), handler)
    vectors = await asyncio.to_thread(embeddings.embed_documents, ["a"])

    assert vectors == [[1.0, 0.0]]
    assert str(seen[0].url) == "http://tei.test/embed"
    assert _inputs(seen[0]) == ["a"]
    assert seen[0].headers["authorization"] == "Bearer secret"


async def test_api_key_is_optional(monkeypatch):
    monkeypatch.delenv("TEI_EMBEDDING_API_KEY", raising=False)
    seen: list[httpx.Request] = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=[[1.0]])

    embeddings = _stub(_TEIEmbeddings(), handler)
    await asyncio.to_thread(embeddings.embed_documents, ["a"])

    assert "authorization" not in seen[0].headers


async def test_batches_at_tei_max_batch_and_preserves_order():
    batches: list[list[str]] = []

    def handler(request):
        batches.append(_inputs(request))
        return _echo_index(request)

    texts = [f"t{i}" for i in range(TEI_MAX_BATCH * 2 + 6)]
    embeddings = _stub(_TEIEmbeddings(), handler)
    vectors = await asyncio.to_thread(embeddings.embed_documents, texts)

    assert [len(b) for b in batches] == [TEI_MAX_BATCH, TEI_MAX_BATCH, 6]
    assert vectors == [[float(i)] for i in range(len(texts))]


async def test_embed_query_returns_one_vector():
    embeddings = _stub(_TEIEmbeddings(), _echo_index)
    assert await asyncio.to_thread(embeddings.embed_query, "t7") == [7.0]


async def test_retries_transient_failure():
    attempts: list[httpx.Request] = []

    def handler(request):
        attempts.append(request)
        if len(attempts) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=[[1.0]])

    embeddings = _stub(_TEIEmbeddings(), handler)
    assert await asyncio.to_thread(embeddings.embed_documents, ["a"]) == [[1.0]]
    assert len(attempts) == 2


async def test_client_error_propagates_without_retry():
    attempts: list[httpx.Request] = []

    def handler(request):
        attempts.append(request)
        return httpx.Response(400)

    embeddings = _stub(_TEIEmbeddings(), handler)
    with pytest.raises(httpx.HTTPStatusError):
        await asyncio.to_thread(embeddings.embed_documents, ["a"])
    assert len(attempts) == 1


async def test_missing_base_url_raises():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.delenv("TEI_EMBEDDING_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="TEI_EMBEDDING_BASE_URL"):
        _TEIEmbeddings()
    monkeypatch.undo()


async def test_batches_are_rate_limited(monkeypatch):
    monkeypatch.setattr(tei, "_limiter", AsyncLimiter(2, 1))
    texts = [f"t{i}" for i in range(TEI_MAX_BATCH * 2 + 1)]

    embeddings = _stub(_TEIEmbeddings(), _echo_index)
    started = time.monotonic()
    await asyncio.to_thread(embeddings.embed_documents, texts)

    assert time.monotonic() - started >= 0.4
