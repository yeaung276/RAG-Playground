import base64

import pytest

from app.config import get_settings
from app.models.agent import Agent
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    Handoff,
    HandoffTarget,
    ToolWrite,
)
from app.services.agents.agent_service import AgentService
from app.services.errors import ConflictError, NotFoundError


@pytest.fixture(autouse=True)
def kek(monkeypatch):
    monkeypatch.setenv("MODEL_KEK", base64.b64encode(b"k" * 32).decode())
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def tool(name: str, **kwargs) -> ToolWrite:
    return ToolWrite(name=name, **kwargs)


async def test_create_persists_fields(db_sessionmaker):
    async with db_sessionmaker() as db:
        agent = await AgentService(db).create(
            AgentCreate(
                name="router",
                description="front door",
                instruction="route the user",
                temperature=30,
                maxStep=5,
                handoff=Handoff(
                    mode="manual", targets=[HandoffTarget(agentId="a2", description="billing")]
                ),
            )
        )
    assert (agent.name, agent.temperature, agent.max_step) == ("router", 30, 5)
    assert agent.handoff.mode == "manual"
    assert agent.handoff.targets[0].agent_id == "a2"
    assert agent.tools == []


async def test_create_defaults_to_no_handoff(db_sessionmaker):
    async with db_sessionmaker() as db:
        agent = await AgentService(db).create(AgentCreate(name="solo"))
    assert agent.handoff.mode == "none"
    assert agent.handoff.targets == []


async def test_duplicate_name_conflicts(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        await service.create(AgentCreate(name="router"))
        with pytest.raises(ConflictError):
            await service.create(AgentCreate(name="router"))


async def test_auth_token_is_encrypted_at_rest(db_sessionmaker):
    async with db_sessionmaker() as db:
        agent = await AgentService(db).create(
            AgentCreate(
                name="router", tools=[tool("search", auth="bearer", authToken="tok-1")]
            )
        )
        row = await db.get(Agent, agent.id)
        stored = row.tools[0]

    assert "tok-1" not in str(stored)
    assert row.tools_dek is not None
    assert agent.tools[0].has_auth_token is True
    # the ciphertext never reaches the read schema
    assert not hasattr(agent.tools[0], "auth_token")


async def test_auth_token_of_round_trips(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        agent = await service.create(
            AgentCreate(
                name="router",
                tools=[
                    tool("search", auth="bearer", authToken="tok-1"),
                    tool("fetch", auth="bearer", authToken="tok-2"),
                ],
            )
        )
        assert await service.auth_token_of(agent.id, "search") == "tok-1"
        assert await service.auth_token_of(agent.id, "fetch") == "tok-2"
        # both tools share the row's single DEK
        assert (await db.get(Agent, agent.id)).tools_dek is not None


async def test_auth_token_of_unknown_tool_raises(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        agent = await service.create(AgentCreate(name="router"))
        with pytest.raises(NotFoundError):
            await service.auth_token_of(agent.id, "nope")


async def test_patch_without_token_keeps_stored_one(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        agent = await service.create(
            AgentCreate(name="router", tools=[tool("search", auth="bearer", authToken="tok-1")])
        )
        updated = await service.update(
            agent.id,
            AgentUpdate(tools=[tool("search", auth="bearer", url="https://example.com")]),
        )
    assert updated.tools[0].url == "https://example.com"
    assert updated.tools[0].has_auth_token is True
    async with db_sessionmaker() as db:
        assert await AgentService(db).auth_token_of(agent.id, "search") == "tok-1"


async def test_patch_with_token_replaces_it(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        agent = await service.create(
            AgentCreate(name="router", tools=[tool("search", auth="bearer", authToken="tok-1")])
        )
        await service.update(
            agent.id, AgentUpdate(tools=[tool("search", auth="bearer", authToken="tok-2")])
        )
        assert await service.auth_token_of(agent.id, "search") == "tok-2"


async def test_patch_is_a_whole_list_keyed_by_name(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        agent = await service.create(
            AgentCreate(
                name="router",
                tools=[tool("search", auth="bearer", authToken="tok-1"), tool("ping")],
            )
        )
        updated = await service.update(
            agent.id,
            AgentUpdate(tools=[tool("search", auth="bearer"), tool("fetch")]),
        )
    # "ping" is absent from the sent list, so it is dropped; "fetch" is created
    assert [t.name for t in updated.tools] == ["search", "fetch"]
    assert [t.has_auth_token for t in updated.tools] == [True, False]


async def test_auth_none_erases_the_token(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        agent = await service.create(
            AgentCreate(name="router", tools=[tool("search", auth="bearer", authToken="tok-1")])
        )
        updated = await service.update(agent.id, AgentUpdate(tools=[tool("search", auth="none")]))
        assert updated.tools[0].has_auth_token is False
        assert await service.auth_token_of(agent.id, "search") is None


async def test_patch_leaves_unsent_fields_alone(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        agent = await service.create(
            AgentCreate(name="router", instruction="route", tools=[tool("search")])
        )
        updated = await service.update(agent.id, AgentUpdate(temperature=80))
    assert updated.temperature == 80
    assert updated.instruction == "route"
    assert [t.name for t in updated.tools] == ["search"]


async def test_patch_replaces_handoff(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        agent = await service.create(
            AgentCreate(
                name="router",
                handoff=Handoff(mode="manual", targets=[HandoffTarget(agentId="a2")]),
            )
        )
        updated = await service.update(agent.id, AgentUpdate(handoff=Handoff(mode="auto")))
    assert updated.handoff.mode == "auto"
    assert updated.handoff.targets == []


async def test_get_list_and_delete(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        first = await service.create(AgentCreate(name="a"))
        await service.create(AgentCreate(name="b"))

        assert [a.name for a in await service.list()] == ["a", "b"]
        assert (await service.get(first.id)).name == "a"

        await service.delete(first.id)
        assert [a.name for a in await service.list()] == ["b"]
        with pytest.raises(NotFoundError):
            await service.get(first.id)


async def test_set_entrypoint_moves_the_flag(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        first = await service.create(AgentCreate(name="a"))
        second = await service.create(AgentCreate(name="b"))
        assert (first.is_entrypoint, second.is_entrypoint) == (False, False)

        assert (await service.set_entrypoint(first.id)).is_entrypoint is True
        assert (await service.set_entrypoint(second.id)).is_entrypoint is True
        # the previous entrypoint is demoted, so only ever one carries the flag
        flags = {a.name: a.is_entrypoint for a in await service.list()}
        assert flags == {"a": False, "b": True}


async def test_set_entrypoint_unknown_agent_raises(db_sessionmaker):
    async with db_sessionmaker() as db:
        with pytest.raises(NotFoundError):
            await AgentService(db).set_entrypoint("nope")


async def test_deleting_the_entrypoint_leaves_none(db_sessionmaker):
    async with db_sessionmaker() as db:
        service = AgentService(db)
        agent = await service.create(AgentCreate(name="a"))
        await service.set_entrypoint(agent.id)
        await service.delete(agent.id)
        await service.create(AgentCreate(name="b"))
        assert [a.is_entrypoint for a in await service.list()] == [False]


async def test_temperature_is_bounded():
    with pytest.raises(ValueError):
        AgentCreate(name="router", temperature=101)
