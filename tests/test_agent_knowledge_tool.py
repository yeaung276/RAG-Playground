from datetime import datetime

import pytest

from app.models.agent import Agent
from app.schemas.agent import (
    AgentCreate,
    AgentRead,
    AgentUpdate,
    Handoff,
    KnowledgeConfig,
)
from app.services.agents.agent_service import AgentService
from app.services.agents.generation_service import GenerationService
from app.services.retrieval.document import Bm25Index, VectorIndex
from app.services.retrieval.retrieval_service import Retrieved

BM25 = [{"type": "bm25"}]


class FakeChunk:
    def __init__(self, content: str):
        self.content = content


class FakeRetrieval:
    """Records the one call the tool makes and returns canned hits."""

    def __init__(self, hits: list[Retrieved] | None = None):
        self.calls: list[tuple[str, str, dict]] = []
        self.hits = hits or []

    async def retrieve(self, kb_id: str, query: str, **kwargs):
        self.calls.append((kb_id, query, kwargs))
        return self.hits


def agent(**kwargs) -> AgentRead:
    now = datetime(2026, 9, 15)
    return AgentRead(
        **{
            "id": "a1",
            "name": "router",
            "description": "",
            "instruction": "",
            "model_id": None,
            "temperature": 0,
            "knowledge_id": None,
            "knowledge_config": None,
            "max_step": 10,
            "tools": [],
            "handoff": Handoff(),
            "is_entrypoint": True,
            "created_at": now,
            "updated_at": now,
            **kwargs,
        }
    )


def service(retrieval: FakeRetrieval) -> GenerationService:
    return GenerationService(None, None, retrieval)


async def test_no_knowledge_means_no_tool():
    tools = await service(FakeRetrieval())._create_default_tools(agent())
    assert tools == []


async def test_a_saved_agent_with_knowledge_binds_the_tool(db_sessionmaker):
    """The whole path: patch through the service, read back, build the tools."""
    async with db_sessionmaker() as db:
        agents = AgentService(db)
        created = await agents.create(AgentCreate(name="router"))
        await agents.update(
            created.id,
            AgentUpdate(
                knowledgeId="kb1",
                knowledgeConfig=KnowledgeConfig(indexTypes=BM25, topK=4),
            ),
        )
        saved = await agents.get(created.id)

    retrieval = FakeRetrieval()
    tools = await service(retrieval)._create_default_tools(saved)
    await tools[0].ainvoke({"query": "refunds"})

    assert [t.name for t in tools] == ["search_knowledge"]
    assert retrieval.calls[0][0] == "kb1"
    assert retrieval.calls[0][2]["top_k"] == 4
    # read back from the JSON column, the indexes still reach retrieval as specs
    assert retrieval.calls[0][2]["index_types"] == [Bm25Index()]


async def test_a_row_with_knowledge_but_no_config_binds_nothing(db_sessionmaker):
    """The state rows already in the database are in: knowledge attached before
    there was a config column. Retrieval is silently skipped."""
    async with db_sessionmaker() as db:
        created = await AgentService(db).create(AgentCreate(name="router"))
        row = await db.get(Agent, created.id)
        row.knowledge_id = "kb1"
        await db.commit()
        await db.refresh(row)
        saved = await AgentService(db).get(created.id)

    assert (saved.knowledge_id, saved.knowledge_config) == ("kb1", None)
    assert await service(FakeRetrieval())._create_default_tools(saved) == []


async def test_attaching_knowledge_without_a_config_is_rejected():
    with pytest.raises(ValueError):
        AgentUpdate(knowledgeId="kb1")


async def test_knowledge_binds_one_search_tool():
    tools = await service(FakeRetrieval())._create_default_tools(
        agent(knowledge_id="kb1", knowledge_config=KnowledgeConfig(indexTypes=BM25))
    )
    assert [t.name for t in tools] == ["search_knowledge"]
    # the model supplies the query and nothing else
    assert list(tools[0].args.keys()) == ["query"]


async def test_stored_config_is_forwarded_to_retrieval():
    retrieval = FakeRetrieval()
    tools = await service(retrieval)._create_default_tools(
        agent(
            knowledge_id="kb1",
            knowledge_config=KnowledgeConfig(
                indexTypes=[{"type": "bm25"}, {"type": "vector", "modelId": "embed-1"}],
                topK=7,
                rerankOn="parent",
            ),
        )
    )
    await tools[0].ainvoke({"query": "refund policy"})

    kb_id, query, kwargs = retrieval.calls[0]
    assert (kb_id, query) == ("kb1", "refund policy")
    assert kwargs["index_types"] == [Bm25Index(), VectorIndex(model_id="embed-1")]
    assert (kwargs["top_k"], kwargs["rerank_on"]) == (7, "parent")
    # unset numbers are dropped so the service's own defaults apply
    assert "rerank_pool" not in kwargs and "prefetch_limit" not in kwargs


async def test_parent_content_is_returned_falling_back_to_the_match():
    retrieval = FakeRetrieval(
        hits=[
            Retrieved(chunk_id="c1", matched_text="child text", chunk=FakeChunk("parent text")),
            Retrieved(chunk_id="c2", matched_text="orphan text", chunk=None),
        ]
    )
    tools = await service(retrieval)._create_default_tools(
        agent(knowledge_id="kb1", knowledge_config=KnowledgeConfig(indexTypes=BM25))
    )
    result = await tools[0].ainvoke({"query": "anything"})

    assert result == "parent text\n\norphan text"
