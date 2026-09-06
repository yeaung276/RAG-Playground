import pytest
from pydantic import ValidationError
from qdrant_client import models

from app.services.knowledge.kb_service import KnowledgeBaseService
from app.services.retrieval.document import EMBEDDING_DIMENSIONS, IndexingConfig


async def _create(db_sessionmaker, qdrant, *index_types):
    async with db_sessionmaker() as session:
        service = KnowledgeBaseService(session, qdrant)
        return await service.create(
            "kb", IndexingConfig(index_types=list(index_types))
        )


async def _layout(qdrant, kb_id: str) -> tuple[dict[str, int], list[str]]:
    """(dense name -> size, sparse names) as the collection actually stands."""
    params = (await qdrant.get_collection(kb_id)).config.params
    return (
        {name: v.size for name, v in (params.vectors or {}).items()},
        sorted((params.sparse_vectors or {}).keys()),
    )


# ── collection layout mirrors index_types ────────────────────────────────────

async def test_sparse_only_kb_has_no_dense_vector(db_sessionmaker, qdrant):
    kb = await _create(db_sessionmaker, qdrant, "bm25")
    assert await _layout(qdrant, kb.id) == ({}, ["bm25"])


async def test_dense_only_kb_has_no_sparse_vector(db_sessionmaker, qdrant):
    kb = await _create(db_sessionmaker, qdrant, "BAAI/bge-m3")
    assert await _layout(qdrant, kb.id) == ({"BAAI/bge-m3": 1024}, [])


async def test_hybrid_kb_has_both(db_sessionmaker, qdrant):
    kb = await _create(db_sessionmaker, qdrant, "BAAI/bge-m3", "bm25")
    assert await _layout(qdrant, kb.id) == ({"BAAI/bge-m3": 1024}, ["bm25"])


async def test_vectors_are_named_after_their_index_type(db_sessionmaker, qdrant):
    kb = await _create(
        db_sessionmaker, qdrant, "text-embedding-3-small", "text-embedding-3-large"
    )
    dense, sparse = await _layout(qdrant, kb.id)
    assert dense == {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072}
    assert sparse == []


async def test_dense_size_comes_from_the_dimension_table(db_sessionmaker, qdrant):
    for model, size in EMBEDDING_DIMENSIONS.items():
        kb = await _create(db_sessionmaker, qdrant, model)
        assert (await _layout(qdrant, kb.id))[0] == {model: size}


async def test_collection_is_named_by_kb_id(db_sessionmaker, qdrant):
    kb = await _create(db_sessionmaker, qdrant, "bm25")
    assert await qdrant.collection_exists(kb.id)


# ── reconfiguration ──────────────────────────────────────────────────────────

async def test_changing_index_types_rebuilds_the_collection(db_sessionmaker, qdrant):
    kb = await _create(db_sessionmaker, qdrant, "bm25")
    async with db_sessionmaker() as session:
        await KnowledgeBaseService(session, qdrant).update_config(
            kb.id, IndexingConfig(index_types=["BAAI/bge-m3"])
        )
    assert await _layout(qdrant, kb.id) == ({"BAAI/bge-m3": 1024}, [])


async def test_adding_an_index_type_keeps_the_rest_of_the_layout(
    db_sessionmaker, qdrant
):
    kb = await _create(db_sessionmaker, qdrant, "bm25")
    async with db_sessionmaker() as session:
        await KnowledgeBaseService(session, qdrant).update_config(
            kb.id, IndexingConfig(index_types=["BAAI/bge-m3", "bm25"])
        )
    assert await _layout(qdrant, kb.id) == ({"BAAI/bge-m3": 1024}, ["bm25"])


async def test_unchanged_index_types_leave_existing_points_alone(
    db_sessionmaker, qdrant
):
    """A rebuild drops every vector, so config edits that don't touch the layout
    must not trigger one."""
    kb = await _create(db_sessionmaker, qdrant, "bm25")
    await qdrant.upsert(
        kb.id,
        points=[
            models.PointStruct(
                id=1,
                vector={"bm25": models.SparseVector(indices=[7], values=[1.0])},
                payload={"chunk_id": "p1"},
            )
        ],
    )

    async with db_sessionmaker() as session:
        await KnowledgeBaseService(session, qdrant).update_config(
            kb.id, IndexingConfig(index_types=["bm25"], max_chunk_size=2000)
        )

    assert (await qdrant.count(kb.id)).count == 1


async def test_reordering_index_types_is_not_a_change(db_sessionmaker, qdrant):
    kb = await _create(db_sessionmaker, qdrant, "BAAI/bge-m3", "bm25")
    await qdrant.upsert(
        kb.id,
        points=[
            models.PointStruct(
                id=1,
                vector={
                    "BAAI/bge-m3": [0.0] * 1024,
                    "bm25": models.SparseVector(indices=[7], values=[1.0]),
                },
                payload={"chunk_id": "p1"},
            )
        ],
    )

    async with db_sessionmaker() as session:
        await KnowledgeBaseService(session, qdrant).update_config(
            kb.id, IndexingConfig(index_types=["bm25", "BAAI/bge-m3"])
        )

    assert (await qdrant.count(kb.id)).count == 1


async def test_deleting_a_kb_drops_its_collection(db_sessionmaker, qdrant):
    kb = await _create(db_sessionmaker, qdrant, "bm25")
    async with db_sessionmaker() as session:
        await KnowledgeBaseService(session, qdrant).delete(kb.id)
    assert not await qdrant.collection_exists(kb.id)


# ── config validation ────────────────────────────────────────────────────────

def test_unknown_index_type_is_rejected():
    with pytest.raises(ValidationError):
        IndexingConfig(index_types=["word2vec"])  # type: ignore[list-item]


def test_index_types_cannot_be_empty():
    with pytest.raises(ValidationError):
        IndexingConfig(index_types=[])


def test_bm25_has_no_declared_dimension():
    assert "bm25" not in EMBEDDING_DIMENSIONS
