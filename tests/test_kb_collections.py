import pytest
import pytest_asyncio
from qdrant_client import models

import app.services.models.model_service as model_service_module
from app.models.model import Model
from app.services.errors import NotFoundError
from app.services.knowledge.kb_service import KnowledgeBaseService
from app.services.models.model_service import ModelService
from app.services.retrieval.document import Bm25Index, KbConfig, VectorIndex

# registered model name -> the vector size its endpoint returns
DIMENSIONS = {"small-embed": 384, "large-embed": 1024}


class FakeTEIEmbedder:
    """Stands in for the TEI client ModelService builds; sizes vectors by model name."""

    probes: list[str] = []

    def __init__(self, model: str, *_args, **_kwargs):
        self.model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        FakeTEIEmbedder.probes.append(self.model)
        return [[0.0] * DIMENSIONS[self.model] for _ in texts]


@pytest.fixture(autouse=True)
def fake_tei(monkeypatch):
    FakeTEIEmbedder.probes = []
    monkeypatch.setattr(model_service_module, "TEIEmbedder", FakeTEIEmbedder)


@pytest_asyncio.fixture
async def embed_ids(db_sessionmaker) -> dict[str, str]:
    """Register each fake model as a TEI bi-encoder; name -> id."""
    async with db_sessionmaker() as session:
        rows = [
            Model(
                provider="local", schema="tei", base_url="http://tei",
                name=name, capability="bi-encoder",
            )
            for name in DIMENSIONS
        ]
        session.add_all(rows)
        await session.commit()
        return {row.name: row.id for row in rows}


def _config(*indexes, **kwargs) -> KbConfig:
    return KbConfig(index_types=list(indexes), **kwargs)


def _vector(model_id: str) -> VectorIndex:
    return VectorIndex(model_id=model_id)


def _service(session, qdrant) -> KnowledgeBaseService:
    return KnowledgeBaseService(session, qdrant, ModelService(session))


async def _create(db_sessionmaker, qdrant, config: KbConfig):
    async with db_sessionmaker() as session:
        return await _service(session, qdrant).create("kb", config)


async def _update(db_sessionmaker, qdrant, kb_id: str, config: KbConfig):
    async with db_sessionmaker() as session:
        return await _service(session, qdrant).update_config(kb_id, config)


async def _layout(qdrant, kb_id: str) -> tuple[dict[str, int], list[str]]:
    """(dense name -> size, sparse names) as the collection actually stands."""
    params = (await qdrant.get_collection(kb_id)).config.params
    return (
        {name: v.size for name, v in (params.vectors or {}).items()},
        sorted((params.sparse_vectors or {}).keys()),
    )


async def _seed_point(qdrant, kb_id: str, vector: dict) -> None:
    await qdrant.upsert(
        kb_id,
        points=[models.PointStruct(id=1, vector=vector, payload={"chunk_id": "p1"})],
    )


# ── collection layout mirrors index_types ────────────────────────────────────

async def test_sparse_only_kb_has_no_dense_vector_and_probes_nothing(
    db_sessionmaker, qdrant
):
    kb = await _create(db_sessionmaker, qdrant, _config(Bm25Index()))
    assert await _layout(qdrant, kb.id) == ({}, ["bm25"])
    assert FakeTEIEmbedder.probes == []


async def test_dense_vector_is_named_by_model_id_and_sized_by_probe(
    db_sessionmaker, qdrant, embed_ids
):
    small = embed_ids["small-embed"]
    kb = await _create(db_sessionmaker, qdrant, _config(_vector(small)))
    assert await _layout(qdrant, kb.id) == ({small: 384}, [])
    assert FakeTEIEmbedder.probes == ["small-embed"]


async def test_hybrid_kb_has_both(db_sessionmaker, qdrant, embed_ids):
    large = embed_ids["large-embed"]
    kb = await _create(db_sessionmaker, qdrant, _config(_vector(large), Bm25Index()))
    assert await _layout(qdrant, kb.id) == ({large: 1024}, ["bm25"])


async def test_each_dense_model_gets_its_own_vector_and_size(
    db_sessionmaker, qdrant, embed_ids
):
    small, large = embed_ids["small-embed"], embed_ids["large-embed"]
    kb = await _create(
        db_sessionmaker, qdrant, _config(_vector(small), _vector(large), Bm25Index())
    )
    assert await _layout(qdrant, kb.id) == ({small: 384, large: 1024}, ["bm25"])
    assert sorted(FakeTEIEmbedder.probes) == ["large-embed", "small-embed"]


async def test_stored_config_is_what_was_sent(db_sessionmaker, qdrant, embed_ids):
    small = embed_ids["small-embed"]
    config = _config(
        Bm25Index(), _vector(small),
        chunking_method="semantic", chunking_model_id=small,
    )
    kb = await _create(db_sessionmaker, qdrant, config)
    assert kb.config == config


async def test_unknown_dense_model_fails_the_create_and_leaves_nothing(
    db_sessionmaker, qdrant
):
    with pytest.raises(NotFoundError):
        await _create(db_sessionmaker, qdrant, _config(_vector("no-such-model")))

    async with db_sessionmaker() as session:
        assert (await _service(session, qdrant).list()) == []
    assert (await qdrant.get_collections()).collections == []


# ── reconfiguration ──────────────────────────────────────────────────────────

async def test_switching_bm25_to_dense_rebuilds_the_collection(
    db_sessionmaker, qdrant, embed_ids
):
    small = embed_ids["small-embed"]
    kb = await _create(db_sessionmaker, qdrant, _config(Bm25Index()))
    await _update(db_sessionmaker, qdrant, kb.id, _config(_vector(small)))
    assert await _layout(qdrant, kb.id) == ({small: 384}, [])


async def test_adding_a_dense_index_keeps_bm25(db_sessionmaker, qdrant, embed_ids):
    small = embed_ids["small-embed"]
    kb = await _create(db_sessionmaker, qdrant, _config(Bm25Index()))
    await _update(db_sessionmaker, qdrant, kb.id, _config(_vector(small), Bm25Index()))
    assert await _layout(qdrant, kb.id) == ({small: 384}, ["bm25"])


async def test_swapping_the_dense_model_rebuilds_with_the_new_name_and_size(
    db_sessionmaker, qdrant, embed_ids
):
    small, large = embed_ids["small-embed"], embed_ids["large-embed"]
    kb = await _create(db_sessionmaker, qdrant, _config(_vector(small)))
    await _seed_point(qdrant, kb.id, {small: [0.0] * 384})

    await _update(db_sessionmaker, qdrant, kb.id, _config(_vector(large)))

    assert await _layout(qdrant, kb.id) == ({large: 1024}, [])
    assert (await qdrant.count(kb.id)).count == 0


async def test_reordering_indexes_is_not_a_change(db_sessionmaker, qdrant, embed_ids):
    small = embed_ids["small-embed"]
    kb = await _create(db_sessionmaker, qdrant, _config(_vector(small), Bm25Index()))
    await _seed_point(
        qdrant, kb.id,
        {small: [0.0] * 384, "bm25": models.SparseVector(indices=[7], values=[1.0])},
    )
    FakeTEIEmbedder.probes = []

    await _update(db_sessionmaker, qdrant, kb.id, _config(Bm25Index(), _vector(small)))

    assert (await qdrant.count(kb.id)).count == 1
    assert FakeTEIEmbedder.probes == []


@pytest.mark.parametrize(
    "changes",
    [
        {"max_chunk_size": 2000},
        {"chunking_method": "fix-sized"},
        {"chunking_method": "semantic", "chunking_model_id": "CHUNK"},
        {"reranker": {"type": "cross-encoder", "modelId": "r1"}},
        {"query_expansion": {"modelId": "chat-1"}},
    ],
    ids=["chunk-size", "chunking-method", "chunking-model", "reranker", "query-expansion"],
)
async def test_non_layout_changes_leave_existing_points_alone(
    db_sessionmaker, qdrant, embed_ids, changes
):
    """A rebuild drops every vector, so edits that don't touch the layout must not
    trigger one."""
    small = embed_ids["small-embed"]
    changes = {
        k: (small if v == "CHUNK" else v) for k, v in changes.items()
    }
    kb = await _create(db_sessionmaker, qdrant, _config(_vector(small)))
    await _seed_point(qdrant, kb.id, {small: [0.0] * 384})

    updated = await _update(
        db_sessionmaker, qdrant, kb.id, KbConfig.model_validate(
            {"index_types": [{"type": "vector", "model_id": small}], **changes}
        ),
    )

    assert (await qdrant.count(kb.id)).count == 1
    assert updated.config.index_types == [_vector(small)]


async def test_failed_probe_on_update_keeps_the_old_config(
    db_sessionmaker, qdrant, embed_ids
):
    kb = await _create(db_sessionmaker, qdrant, _config(Bm25Index()))

    with pytest.raises(NotFoundError):
        await _update(db_sessionmaker, qdrant, kb.id, _config(_vector("no-such-model")))

    async with db_sessionmaker() as session:
        assert (await _service(session, qdrant).get(kb.id)).config == _config(Bm25Index())


async def test_deleting_a_kb_drops_its_collection(db_sessionmaker, qdrant):
    kb = await _create(db_sessionmaker, qdrant, _config(Bm25Index()))
    async with db_sessionmaker() as session:
        await _service(session, qdrant).delete(kb.id)
    assert not await qdrant.collection_exists(kb.id)
