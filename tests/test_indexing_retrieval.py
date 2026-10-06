import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select

import app.services.models.model_service as model_service_module
from app.models.chunk import Chunk as ChunkRow
from app.models.model import Model
from app.models.node import Node
from app.services.knowledge.kb_service import KnowledgeBaseService
from app.services.models.model_service import ModelService
from app.services.retrieval.document import (
    Bm25Index,
    CrossEncoderReranker,
    Document,
    KbConfig,
    LateInteractionReranker,
    Page,
    VectorIndex,
)
from app.services.retrieval.indexing_service import IndexingService
from app.services.retrieval.retrieval_service import RetrievalService

DIM = 8

# The tokenizer indexes a term only if it carries a letter or digit, so this marker
# is invisible to bm25 — letting a test attribute a hit to the dense branch alone.
DENSE_MARKER = "@@"


class FakeTEIEmbedder:
    """Deterministic vectors: text carrying DENSE_MARKER points along axis 1,
    everything else along axis 0. Records which registered model embedded what."""

    calls: list[tuple[str, int]] = []
    explode: bool = False

    def __init__(self, model: str, *_args, **_kwargs):
        self.model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if FakeTEIEmbedder.explode:
            raise AssertionError(f"{self.model} embedded when it should not have")
        FakeTEIEmbedder.calls.append((self.model, len(texts)))
        out = []
        for text in texts:
            vector = [0.0] * DIM
            vector[1 if DENSE_MARKER in text else 0] = 1.0
            out.append(vector)
        return out


class FakeTEIReranker:
    """Scores a text by how often it says "winner", recording what it was shown."""

    seen: list[tuple[str, str, list[str]]] = []

    def __init__(self, model: str, *_args, **_kwargs):
        self.model = model

    async def rank(self, query: str, texts: list[str]) -> list[float]:
        FakeTEIReranker.seen.append((self.model, query, texts))
        return [float(t.count("winner")) for t in texts]


@pytest.fixture(autouse=True)
def fake_endpoints(monkeypatch):
    FakeTEIEmbedder.calls = []
    FakeTEIEmbedder.explode = False
    FakeTEIReranker.seen = []
    monkeypatch.setattr(model_service_module, "TEIEmbedder", FakeTEIEmbedder)
    monkeypatch.setattr(model_service_module, "TEIReranker", FakeTEIReranker)


@pytest_asyncio.fixture
async def ids(db_sessionmaker) -> dict[str, str]:
    """Registered TEI models; name -> id."""
    async with db_sessionmaker() as session:
        rows = [
            Model(provider="local", schema="tei", base_url="http://tei",
                  name=name, capability=capability)
            for name, capability in [
                ("dense-a", "bi-encoder"),
                ("dense-b", "bi-encoder"),
                ("chunker", "bi-encoder"),
                ("reranker", "cross-encoder"),
            ]
        ]
        session.add_all(rows)
        await session.commit()
        return {row.name: row.id for row in rows}


def _doc(source: str, *markdowns: str) -> Document:
    return Document(
        source=source,
        pages=[Page(index=i, markdown=m) for i, m in enumerate(markdowns)],
    )


async def _setup(db_sessionmaker, qdrant, *indexes, **config):
    """A fresh KB with its collection, plus one file node to hang chunks off."""
    config = KbConfig(index_types=list(indexes), **config)
    async with db_sessionmaker() as session:
        kb = await KnowledgeBaseService(session, qdrant, ModelService(session)).create(
            "kb", config
        )
    async with db_sessionmaker() as session:
        node = Node(kb_id=kb.id, name="a.md", type="file")
        session.add(node)
        await session.flush()
        node_id = node.id
        await session.commit()
    FakeTEIEmbedder.calls = []  # drop the collection-size probes
    return kb.id, node_id, config


async def _index(db_sessionmaker, qdrant, kb_id, node_id, config, docs):
    indexer = IndexingService(db_sessionmaker, qdrant)
    for source, text in docs:
        await indexer.create_index(_doc(source, text), config, node_id=node_id, kb_id=kb_id)


async def _vector_names(qdrant, kb_id) -> list[set[str]]:
    points = (await qdrant.scroll(kb_id, limit=100, with_vectors=True))[0]
    return [set(p.vector) for p in points]  # type: ignore[arg-type]


# ── indexing: which models embed ─────────────────────────────────────────────

async def test_bm25_only_needs_no_registered_model(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, Bm25Index())
    await _index(db_sessionmaker, qdrant, kb_id, node_id, config, [("a.md", "alpha beta")])

    assert all(names == {"bm25"} for names in await _vector_names(qdrant, kb_id))
    assert FakeTEIEmbedder.calls == []


async def test_dense_index_embeds_with_the_registered_model(db_sessionmaker, qdrant, ids):
    a = ids["dense-a"]
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, VectorIndex(model_id=a))
    await _index(db_sessionmaker, qdrant, kb_id, node_id, config, [("a.md", "alpha beta")])

    names = await _vector_names(qdrant, kb_id)
    assert names and all(n == {a} for n in names)
    assert {model for model, _ in FakeTEIEmbedder.calls} == {"dense-a"}


async def test_every_configured_index_lands_on_every_point(db_sessionmaker, qdrant, ids):
    a, b = ids["dense-a"], ids["dense-b"]
    kb_id, node_id, config = await _setup(
        db_sessionmaker, qdrant,
        Bm25Index(), VectorIndex(model_id=a), VectorIndex(model_id=b),
    )
    await _index(db_sessionmaker, qdrant, kb_id, node_id, config, [("a.md", "alpha beta")])

    names = await _vector_names(qdrant, kb_id)
    assert names and all(n == {"bm25", a, b} for n in names)
    assert {model for model, _ in FakeTEIEmbedder.calls} == {"dense-a", "dense-b"}


async def test_unregistered_dense_model_fails_before_anything_is_written(
    db_sessionmaker, qdrant, ids
):
    kb_id, node_id, _ = await _setup(db_sessionmaker, qdrant, Bm25Index())
    bad = KbConfig(index_types=[Bm25Index(), VectorIndex(model_id="gone")])

    with pytest.raises(HTTPException) as exc:
        await _index(db_sessionmaker, qdrant, kb_id, node_id, bad, [("a.md", "alpha")])

    assert exc.value.status_code == 404
    assert (await qdrant.count(kb_id)).count == 0
    async with db_sessionmaker() as session:
        assert (await session.execute(select(ChunkRow))).scalars().all() == []


# ── indexing: chunking model ─────────────────────────────────────────────────

async def test_semantic_chunking_uses_the_chunking_model_not_the_index_model(
    db_sessionmaker, qdrant, ids
):
    kb_id, node_id, config = await _setup(
        db_sessionmaker, qdrant, VectorIndex(model_id=ids["dense-a"]),
        chunking_method="semantic", chunking_model_id=ids["chunker"],
        max_chunk_size=400, min_chunk_size=10,
    )
    text = "Coins are round. Coins are minted. " * 5 + "Rivers flow. Rivers flood. " * 5
    await _index(db_sessionmaker, qdrant, kb_id, node_id, config, [("a.md", text)])

    models_used = [model for model, _ in FakeTEIEmbedder.calls]
    assert "chunker" in models_used
    assert "dense-a" in models_used
    assert (await qdrant.count(kb_id)).count > 0


@pytest.mark.parametrize("method", ["fix-sized", "recursive"])
async def test_non_semantic_chunking_never_calls_the_chunking_model(
    db_sessionmaker, qdrant, ids, method
):
    kb_id, node_id, config = await _setup(
        db_sessionmaker, qdrant, Bm25Index(),
        chunking_method=method, chunking_model_id=ids["chunker"],
    )
    await _index(db_sessionmaker, qdrant, kb_id, node_id, config, [("a.md", "alpha " * 50)])
    assert FakeTEIEmbedder.calls == []


async def test_unregistered_chunking_model_fails_the_index(db_sessionmaker, qdrant):
    kb_id, node_id, _ = await _setup(db_sessionmaker, qdrant, Bm25Index())
    bad = KbConfig(chunking_method="semantic", chunking_model_id="gone")

    with pytest.raises(HTTPException) as exc:
        await _index(db_sessionmaker, qdrant, kb_id, node_id, bad, [("a.md", "alpha")])
    assert exc.value.status_code == 404
    assert (await qdrant.count(kb_id)).count == 0


# ── delete_index ─────────────────────────────────────────────────────────────

async def _add_node(db_sessionmaker, kb_id: str, name: str) -> str:
    async with db_sessionmaker() as session:
        node = Node(kb_id=kb_id, name=name, type="file")
        session.add(node)
        await session.commit()
        return node.id


async def _node_ids(qdrant, kb_id) -> set[str]:
    points = (await qdrant.scroll(kb_id, limit=100))[0]
    return {p.payload["node_id"] for p in points}  # type: ignore[index]


async def test_delete_index_drops_only_that_nodes_points(db_sessionmaker, qdrant, ids):
    kb_id, keep, config = await _setup(
        db_sessionmaker, qdrant, Bm25Index(), VectorIndex(model_id=ids["dense-a"])
    )
    drop = await _add_node(db_sessionmaker, kb_id, "b.md")
    indexer = IndexingService(db_sessionmaker, qdrant)
    await indexer.create_index(_doc("a.md", "alpha " * 300), config, node_id=keep, kb_id=kb_id)
    await indexer.create_index(_doc("b.md", "beta " * 300), config, node_id=drop, kb_id=kb_id)
    assert await _node_ids(qdrant, kb_id) == {keep, drop}

    await indexer.delete_index(node_id=drop, kb_id=kb_id)

    assert await _node_ids(qdrant, kb_id) == {keep}


async def test_delete_index_for_a_node_with_no_points_is_a_no_op(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, Bm25Index())
    await _index(db_sessionmaker, qdrant, kb_id, node_id, config, [("a.md", "alpha")])
    before = (await qdrant.count(kb_id)).count

    await IndexingService(db_sessionmaker, qdrant).delete_index(node_id="never-indexed", kb_id=kb_id)

    assert (await qdrant.count(kb_id)).count == before


# ── retrieval: choosing from what the KB offers ──────────────────────────────

async def test_retrieve_returns_parent_chunks_ranked_lexically(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, Bm25Index())
    await _index(
        db_sessionmaker, qdrant, kb_id, node_id, config,
        [("a.md", "gardening tips for tomatoes"), ("b.md", "qdrant stores sparse vectors")],
    )

    hits = await RetrievalService(db_sessionmaker, qdrant).retrieve(
        kb_id, "sparse vectors", index_types=[Bm25Index()]
    )
    assert "sparse vectors" in hits[0].chunk.content
    async with db_sessionmaker() as session:
        parent_ids = {r.id for r in (await session.execute(select(ChunkRow))).scalars()}
    assert all(h.chunk.id in parent_ids for h in hits)


async def test_hybrid_retrieval_fuses_both_indexes(db_sessionmaker, qdrant, ids):
    """One doc is reachable only lexically, the other only densely. Fusion must
    surface both; bm25 alone must not."""
    a = ids["dense-a"]
    kb_id, node_id, config = await _setup(
        db_sessionmaker, qdrant, VectorIndex(model_id=a), Bm25Index()
    )
    await _index(
        db_sessionmaker, qdrant, kb_id, node_id, config,
        [("lexical.md", "pelicans share the cliffs"),
         ("dense.md", f"{DENSE_MARKER} covers something else")],
    )
    service = RetrievalService(db_sessionmaker, qdrant)
    query = f"pelicans {DENSE_MARKER}"

    lexical = await service.retrieve(kb_id, query, index_types=[Bm25Index()], top_k=5)
    assert [h.chunk.content for h in lexical] == ["pelicans share the cliffs"]

    fused = await service.retrieve(
        kb_id, query, index_types=[VectorIndex(model_id=a), Bm25Index()], top_k=5
    )
    contents = " ".join(h.chunk.content for h in fused)
    assert "pelicans" in contents and DENSE_MARKER in contents


async def test_dense_only_retrieval_from_a_hybrid_kb(db_sessionmaker, qdrant, ids):
    a = ids["dense-a"]
    kb_id, node_id, config = await _setup(
        db_sessionmaker, qdrant, VectorIndex(model_id=a), Bm25Index()
    )
    await _index(
        db_sessionmaker, qdrant, kb_id, node_id, config,
        [("dense.md", f"{DENSE_MARKER} only the dense side sees this")],
    )
    FakeTEIEmbedder.calls = []

    hits = await RetrievalService(db_sessionmaker, qdrant).retrieve(
        kb_id, DENSE_MARKER, index_types=[VectorIndex(model_id=a)]
    )
    assert DENSE_MARKER in hits[0].chunk.content
    assert FakeTEIEmbedder.calls == [("dense-a", 1)]


async def test_retrieval_picks_one_of_two_dense_models(db_sessionmaker, qdrant, ids):
    a, b = ids["dense-a"], ids["dense-b"]
    kb_id, node_id, config = await _setup(
        db_sessionmaker, qdrant, VectorIndex(model_id=a), VectorIndex(model_id=b)
    )
    await _index(db_sessionmaker, qdrant, kb_id, node_id, config, [("a.md", "alpha")])
    FakeTEIEmbedder.calls = []

    await RetrievalService(db_sessionmaker, qdrant).retrieve(
        kb_id, "alpha", index_types=[VectorIndex(model_id=b)]
    )
    assert FakeTEIEmbedder.calls == [("dense-b", 1)]


@pytest.mark.parametrize(
    "kb_indexes, requested",
    [
        (["bm25"], ["dense-a"]),
        (["bm25"], ["bm25", "dense-a"]),
        (["dense-a"], ["bm25"]),
        (["dense-a"], ["dense-b"]),
    ],
    ids=["dense-on-sparse-kb", "partly-missing", "sparse-on-dense-kb", "other-dense-model"],
)
async def test_requesting_an_index_the_kb_lacks_is_a_409_before_embedding(
    db_sessionmaker, qdrant, ids, kb_indexes, requested
):
    def spec(name):
        return Bm25Index() if name == "bm25" else VectorIndex(model_id=ids[name])

    kb_id, _, _ = await _setup(db_sessionmaker, qdrant, *map(spec, kb_indexes))
    FakeTEIEmbedder.explode = True

    with pytest.raises(HTTPException) as exc:
        await RetrievalService(db_sessionmaker, qdrant).retrieve(
            kb_id, "q", index_types=list(map(spec, requested))
        )
    assert exc.value.status_code == 409
    assert kb_id in exc.value.detail


async def test_retrieve_404s_on_unknown_kb(db_sessionmaker, qdrant):
    with pytest.raises(HTTPException) as exc:
        await RetrievalService(db_sessionmaker, qdrant).retrieve(
            "does-not-exist", "q", index_types=[Bm25Index()]
        )
    assert exc.value.status_code == 404


# ── retrieval: reranking only when the KB has a reranker ─────────────────────

async def _rerank_kb(db_sessionmaker, qdrant, reranker):
    kb_id, node_id, config = await _setup(
        db_sessionmaker, qdrant, Bm25Index(), reranker=reranker
    )
    await _index(
        db_sessionmaker, qdrant, kb_id, node_id, config,
        [("a.md", "coins coins coins"), ("b.md", "coins winner winner")],
    )
    return kb_id


async def test_rerank_without_a_kb_reranker_is_a_409_before_embedding(
    db_sessionmaker, qdrant
):
    kb_id = await _rerank_kb(db_sessionmaker, qdrant, None)
    FakeTEIEmbedder.explode = True

    with pytest.raises(HTTPException) as exc:
        await RetrievalService(db_sessionmaker, qdrant).retrieve(
            kb_id, "coins", index_types=[Bm25Index()], rerank_on="parent"
        )
    assert exc.value.status_code == 409
    assert FakeTEIReranker.seen == []


@pytest.mark.parametrize("rerank_on", ["parent", "child"])
async def test_rerank_uses_the_kb_reranker_model(db_sessionmaker, qdrant, ids, rerank_on):
    kb_id = await _rerank_kb(
        db_sessionmaker, qdrant, CrossEncoderReranker(model_id=ids["reranker"])
    )

    hits = await RetrievalService(db_sessionmaker, qdrant).retrieve(
        kb_id, "coins", index_types=[Bm25Index()], rerank_on=rerank_on, top_k=2
    )

    assert hits[0].chunk.content == "coins winner winner"
    assert [h.score for h in hits] == [2.0, 0.0]
    [(model, query, texts)] = FakeTEIReranker.seen
    assert (model, query) == ("reranker", "coins")
    assert sorted(texts) == ["coins coins coins", "coins winner winner"]


async def test_configured_reranker_is_not_used_unless_asked(db_sessionmaker, qdrant, ids):
    kb_id = await _rerank_kb(
        db_sessionmaker, qdrant, CrossEncoderReranker(model_id=ids["reranker"])
    )
    await RetrievalService(db_sessionmaker, qdrant).retrieve(
        kb_id, "coins", index_types=[Bm25Index()]
    )
    assert FakeTEIReranker.seen == []


async def test_late_interaction_reranker_is_not_supported_yet(db_sessionmaker, qdrant, ids):
    kb_id = await _rerank_kb(
        db_sessionmaker, qdrant, LateInteractionReranker(model_id=ids["dense-a"])
    )
    with pytest.raises(ValueError, match="Unsupported reranker"):
        await RetrievalService(db_sessionmaker, qdrant).retrieve(
            kb_id, "coins", index_types=[Bm25Index()], rerank_on="parent"
        )


async def test_reranker_model_that_is_gone_is_a_404(db_sessionmaker, qdrant):
    kb_id = await _rerank_kb(
        db_sessionmaker, qdrant, CrossEncoderReranker(model_id="gone")
    )
    with pytest.raises(HTTPException) as exc:
        await RetrievalService(db_sessionmaker, qdrant).retrieve(
            kb_id, "coins", index_types=[Bm25Index()], rerank_on="parent"
        )
    assert exc.value.status_code == 404
