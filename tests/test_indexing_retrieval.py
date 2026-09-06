import pytest
from fastapi import HTTPException
from sqlalchemy import select

import app.services.retrieval.indexing_service as indexing_module
import app.services.retrieval.retrieval_service as retrieval_module
from app.models.chunk import Chunk as ChunkRow
from app.models.node import Node
from app.services.knowledge.kb_service import KnowledgeBaseService
from app.services.retrieval.document import Document, IndexingConfig, Page
from app.services.retrieval.indexing_service import IndexingService
from app.services.retrieval.retrieval_service import RetrievalService

DENSE = "BAAI/bge-m3"
DIM = 1024


# The tokenizer indexes a term only if it carries a letter or digit, so this marker
# is invisible to bm25 — letting a test attribute a hit to the dense branch alone.
DENSE_MARKER = "@@"


class FakeDense:
    """Deterministic 1024-d vectors: text carrying DENSE_MARKER points along axis 1,
    everything else along axis 0, so dense similarity is decidable without TEI."""

    def __init__(self, model: str = DENSE, *_args, **_kwargs):
        self.model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vector = [0.0] * DIM
            vector[1 if DENSE_MARKER in text else 0] = 1.0
            out.append(vector)
        return out


@pytest.fixture(autouse=True)
def fake_dense(monkeypatch):
    """Both services construct TEIEmbedder by name; swap it so no TEI is needed."""
    monkeypatch.setattr(indexing_module, "TEIEmbedder", FakeDense)
    monkeypatch.setattr(retrieval_module, "TEIEmbedder", FakeDense)


def _config(*index_types: str) -> IndexingConfig:
    return IndexingConfig(
        chunking_method="recursive", index_types=list(index_types)  # type: ignore[arg-type]
    )


def _doc(source: str, *markdowns: str) -> Document:
    return Document(
        source=source,
        pages=[Page(index=i, markdown=m) for i, m in enumerate(markdowns)],
    )


async def _setup(db_sessionmaker, qdrant, *index_types: str):
    """A fresh KB with its collection, plus one file node to hang chunks off."""
    config = _config(*index_types)
    async with db_sessionmaker() as session:
        kb = await KnowledgeBaseService(session, qdrant).create("kb", config)
    async with db_sessionmaker() as session:
        node = Node(kb_id=kb.id, name="a.md", type="file")
        session.add(node)
        await session.flush()
        node_id = node.id
        await session.commit()
    return kb.id, node_id, config


# ── indexing ─────────────────────────────────────────────────────────────────

async def test_index_persists_parents_to_postgres(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, "bm25")
    await IndexingService(db_sessionmaker, qdrant).create_index(
        _doc("a.md", "the coin is round. " * 60), config, node_id=node_id, kb_id=kb_id
    )

    async with db_sessionmaker() as session:
        rows = (await session.execute(select(ChunkRow))).scalars().all()
    assert rows
    assert {r.kb_id for r in rows} == {kb_id}
    assert sorted(r.seq for r in rows) == list(range(len(rows)))


async def test_index_upserts_one_point_per_child(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, "bm25")
    await IndexingService(db_sessionmaker, qdrant).create_index(
        _doc("a.md", "the coin is round. " * 60), config, node_id=node_id, kb_id=kb_id
    )
    assert (await qdrant.count(kb_id)).count > 0


async def test_sparse_only_kb_emits_only_the_sparse_vector(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, "bm25")
    await IndexingService(db_sessionmaker, qdrant).create_index(
        _doc("a.md", "alpha beta gamma"), config, node_id=node_id, kb_id=kb_id
    )
    points = (await qdrant.scroll(kb_id, limit=10, with_vectors=True))[0]
    assert all(set(p.vector) == {"bm25"} for p in points)  # type: ignore[arg-type]


async def test_dense_only_kb_emits_only_the_dense_vector(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, DENSE)
    await IndexingService(db_sessionmaker, qdrant).create_index(
        _doc("a.md", "alpha beta gamma"), config, node_id=node_id, kb_id=kb_id
    )
    points = (await qdrant.scroll(kb_id, limit=10, with_vectors=True))[0]
    assert all(set(p.vector) == {DENSE} for p in points)  # type: ignore[arg-type]


async def test_hybrid_kb_emits_both_vectors_on_every_point(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, DENSE, "bm25")
    await IndexingService(db_sessionmaker, qdrant).create_index(
        _doc("a.md", "alpha beta gamma"), config, node_id=node_id, kb_id=kb_id
    )
    points = (await qdrant.scroll(kb_id, limit=10, with_vectors=True))[0]
    assert points
    assert all(set(p.vector) == {DENSE, "bm25"} for p in points)  # type: ignore[arg-type]


async def test_point_payload_links_back_to_parent_and_node(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, "bm25")
    await IndexingService(db_sessionmaker, qdrant).create_index(
        _doc("a.md", "alpha beta gamma"), config, node_id=node_id, kb_id=kb_id
    )
    point = (await qdrant.scroll(kb_id, limit=1))[0][0]

    async with db_sessionmaker() as session:
        parent_ids = {
            r.id for r in (await session.execute(select(ChunkRow))).scalars().all()
        }
    assert point.payload["chunk_id"] in parent_ids  # type: ignore[index]
    assert point.payload["node_id"] == node_id  # type: ignore[index]
    assert point.payload["source"] == "a.md"  # type: ignore[index]
    # the collection *is* the kb, so the payload doesn't repeat it
    assert "kb_id" not in point.payload  # type: ignore[operator]


async def test_point_payload_carries_parent_pages(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, "bm25")
    await IndexingService(db_sessionmaker, qdrant).create_index(
        _doc("a.md", "alpha", "beta"), config, node_id=node_id, kb_id=kb_id
    )
    points = (await qdrant.scroll(kb_id, limit=10))[0]
    assert all(p.payload["pages"] == [0, 1] for p in points)  # type: ignore[index]


async def test_indexing_an_empty_document_writes_nothing(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, "bm25")
    await IndexingService(db_sessionmaker, qdrant).create_index(
        _doc("empty.md"), config, node_id=node_id, kb_id=kb_id
    )
    assert (await qdrant.count(kb_id)).count == 0


async def test_unsupported_index_type_is_rejected_at_resolution(
    db_sessionmaker, qdrant
):
    service = IndexingService(db_sessionmaker, qdrant)
    with pytest.raises(ValueError, match="Unsupported index type"):
        service._get_embedding_model_from_config(
            IndexingConfig.model_construct(index_types=["word2vec"])
        )


# ── retrieval ────────────────────────────────────────────────────────────────

async def _index_docs(db_sessionmaker, qdrant, kb_id, node_id, config, docs):
    indexer = IndexingService(db_sessionmaker, qdrant)
    for source, text in docs:
        await indexer.create_index(
            _doc(source, text), config, node_id=node_id, kb_id=kb_id
        )


async def test_retrieve_returns_parent_chunks_not_children(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, "bm25")
    await _index_docs(
        db_sessionmaker, qdrant, kb_id, node_id, config,
        [("a.md", "pelicans nest on the cliffs " * 40)],
    )

    hits = await RetrievalService(db_sessionmaker, qdrant).retrieve(
        kb_id, "pelicans", index_types=["bm25"]
    )
    assert hits
    async with db_sessionmaker() as session:
        parent_ids = {
            r.id for r in (await session.execute(select(ChunkRow))).scalars().all()
        }
    assert all(h.chunk.id in parent_ids for h in hits)


async def test_retrieve_ranks_the_lexical_match_first(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, "bm25")
    await _index_docs(
        db_sessionmaker, qdrant, kb_id, node_id, config,
        [
            ("a.md", "gardening tips for tomatoes and basil"),
            ("b.md", "qdrant stores sparse vectors for retrieval"),
        ],
    )

    hits = await RetrievalService(db_sessionmaker, qdrant).retrieve(
        kb_id, "sparse vectors", index_types=["bm25"]
    )
    assert hits
    assert "sparse vectors" in hits[0].chunk.content


async def test_retrieve_scores_are_descending(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, "bm25")
    await _index_docs(
        db_sessionmaker, qdrant, kb_id, node_id, config,
        [(f"{i}.md", f"document {i} about retrieval") for i in range(5)],
    )

    hits = await RetrievalService(db_sessionmaker, qdrant).retrieve(
        kb_id, "retrieval", index_types=["bm25"], top_k=5
    )
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)


async def test_retrieve_honours_top_k(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, "bm25")
    await _index_docs(
        db_sessionmaker, qdrant, kb_id, node_id, config,
        [(f"{i}.md", f"document {i} about retrieval") for i in range(5)],
    )

    hits = await RetrievalService(db_sessionmaker, qdrant).retrieve(
        kb_id, "retrieval", index_types=["bm25"], top_k=2
    )
    assert len(hits) == 2


async def test_retrieve_collapses_children_to_one_hit_per_parent(
    db_sessionmaker, qdrant
):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, "bm25")
    await _index_docs(
        db_sessionmaker, qdrant, kb_id, node_id, config,
        [("a.md", "retrieval " * 400)],  # many children, all under one parent
    )
    assert (await qdrant.count(kb_id)).count > 1

    hits = await RetrievalService(db_sessionmaker, qdrant).retrieve(
        kb_id, "retrieval", index_types=["bm25"], top_k=10
    )
    assert len({h.chunk.id for h in hits}) == len(hits)


async def test_retrieve_on_empty_kb_returns_nothing(db_sessionmaker, qdrant):
    kb_id, _, _ = await _setup(db_sessionmaker, qdrant, "bm25")
    hits = await RetrievalService(db_sessionmaker, qdrant).retrieve(
        kb_id, "anything", index_types=["bm25"]
    )
    assert hits == []


async def test_retrieve_uses_both_indices_when_hybrid(db_sessionmaker, qdrant):
    """One doc is reachable only lexically, the other only densely (its marker is
    invisible to the tokenizer). Fusion must surface both; bm25 alone must not."""
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, DENSE, "bm25")
    await _index_docs(
        db_sessionmaker, qdrant, kb_id, node_id, config,
        [
            ("lexical.md", "pelicans and cormorants share the cliffs"),
            ("dense.md", f"{DENSE_MARKER} covers something else entirely"),
        ],
    )
    service = RetrievalService(db_sessionmaker, qdrant)
    query = f"pelicans {DENSE_MARKER}"

    lexical_only = await service.retrieve(kb_id, query, index_types=["bm25"], top_k=5)
    assert [h.chunk.content for h in lexical_only] == [
        "pelicans and cormorants share the cliffs"
    ]

    fused = await service.retrieve(kb_id, query, index_types=[DENSE, "bm25"], top_k=5)
    contents = " ".join(h.chunk.content for h in fused)
    assert "pelicans" in contents
    assert DENSE_MARKER in contents


# ── retrieval guards ─────────────────────────────────────────────────────────

async def test_retrieve_404s_on_unknown_kb(db_sessionmaker, qdrant):
    with pytest.raises(HTTPException) as exc:
        await RetrievalService(db_sessionmaker, qdrant).retrieve(
            "does-not-exist", "q", index_types=["bm25"]
        )
    assert exc.value.status_code == 404


async def test_retrieve_409s_on_index_the_kb_lacks(db_sessionmaker, qdrant):
    kb_id, _, _ = await _setup(db_sessionmaker, qdrant, "bm25")
    with pytest.raises(HTTPException) as exc:
        await RetrievalService(db_sessionmaker, qdrant).retrieve(
            kb_id, "q", index_types=[DENSE]
        )
    assert exc.value.status_code == 409
    assert kb_id in exc.value.detail


async def test_retrieve_409s_when_only_some_indices_are_missing(db_sessionmaker, qdrant):
    kb_id, _, _ = await _setup(db_sessionmaker, qdrant, "bm25")
    with pytest.raises(HTTPException) as exc:
        await RetrievalService(db_sessionmaker, qdrant).retrieve(
            kb_id, "q", index_types=["bm25", DENSE]
        )
    assert exc.value.status_code == 409


async def test_retrieve_accepts_a_subset_of_the_kb_indices(db_sessionmaker, qdrant):
    kb_id, node_id, config = await _setup(db_sessionmaker, qdrant, DENSE, "bm25")
    await _index_docs(
        db_sessionmaker, qdrant, kb_id, node_id, config,
        [("a.md", "pelicans nest on the cliffs")],
    )
    hits = await RetrievalService(db_sessionmaker, qdrant).retrieve(
        kb_id, "pelicans", index_types=["bm25"]
    )
    assert hits


async def test_retrieve_guard_runs_before_any_embedding(
    db_sessionmaker, qdrant, monkeypatch
):
    """The rejection must not cost an embedding call."""
    kb_id, _, _ = await _setup(db_sessionmaker, qdrant, "bm25")

    class Exploding(FakeDense):
        async def embed(self, texts):
            raise AssertionError("embedded despite an invalid index type")

    monkeypatch.setattr(retrieval_module, "TEIEmbedder", Exploding)
    with pytest.raises(HTTPException):
        await RetrievalService(db_sessionmaker, qdrant).retrieve(
            kb_id, "q", index_types=[DENSE]
        )
