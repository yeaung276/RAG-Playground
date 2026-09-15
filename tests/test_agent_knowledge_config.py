import pytest

from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate, KnowledgeConfig
from app.services.agents.agent_service import AgentService


def config(**kwargs) -> KnowledgeConfig:
    return KnowledgeConfig(**{"indexTypes": ["bm25"], **kwargs})


async def test_patch_stores_camel_case_keys(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        agent = await service.create(AgentCreate(name="router"))
        read = await service.update(
            agent.id,
            AgentUpdate(knowledgeConfig=config(topK=8, rerankOn="child", rerankPool=20)),
        )
        stored = (await db.get(Agent, agent.id)).knowledge_config

    # the column holds the wire shape, like `handoff` does
    assert stored == {
        "indexTypes": ["bm25"],
        "topK": 8,
        "rerankOn": "child",
        "rerankPool": 20,
        "prefetchLimit": None,
    }
    assert (read.knowledge_config.top_k, read.knowledge_config.rerank_on) == (8, "child")


async def test_patching_null_clears_it(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        agent = await service.create(AgentCreate(name="router"))
        await service.update(agent.id, AgentUpdate(knowledgeConfig=config(topK=3)))

        read = await service.update(agent.id, AgentUpdate(knowledgeConfig=None))
        assert read.knowledge_config is None
        assert (await db.get(Agent, agent.id)).knowledge_config is None


async def test_patching_other_fields_leaves_it_alone(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        agent = await service.create(AgentCreate(name="router"))
        await service.update(agent.id, AgentUpdate(knowledgeConfig=config(topK=3)))

        read = await service.update(agent.id, AgentUpdate(temperature=50))
        assert read.knowledge_config.top_k == 3


async def test_unknown_index_type_is_rejected():
    with pytest.raises(ValueError):
        KnowledgeConfig(indexTypes=["not-an-index"])


async def test_at_least_one_index_type_is_required():
    with pytest.raises(ValueError):
        KnowledgeConfig(indexTypes=[])
    with pytest.raises(ValueError):
        KnowledgeConfig()


async def test_empty_index_types_are_rejected_by_the_route(client):
    agent = (await client.post("/api/admin/agents", json={"name": "router"})).json()
    response = await client.patch(
        f"/api/admin/agents/{agent['id']}",
        json={"knowledgeConfig": {"indexTypes": [], "topK": 5}},
    )
    assert response.status_code == 422


async def test_counts_must_be_positive():
    for field in ("topK", "rerankPool", "prefetchLimit"):
        with pytest.raises(ValueError):
            KnowledgeConfig(**{field: 0})
