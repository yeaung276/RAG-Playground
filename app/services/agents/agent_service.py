from __future__ import annotations

import base64
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.schemas.agent import (
    AgentCreate,
    AgentRead,
    AgentSummary,
    AgentUpdate,
    AuthKind,
    Handoff,
    ToolRead,
    ToolTestRequest,
    ToolTestResult,
    ToolWrite,
)
from app.services.agents import tool_runner
from app.services.errors import ConflictError, NotFoundError
from app.utils.crypto import decrypt_secret, encrypt_secret

_CT = "authTokenCt"


class AgentService:
    """CRUD for configured agents. `tools` is a whole-document column keyed by
    tool name; each tool's auth token is sealed under the row's `tools_dek` and
    only leaves this service through `auth_token_of`."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payload: AgentCreate) -> AgentRead:
        agent = Agent(
            name=payload.name,
            description=payload.description,
            instruction=payload.instruction,
            model_id=payload.model_id,
            temperature=payload.temperature,
            knowledge_id=payload.knowledge_id,
            max_step=payload.max_step,
            handoff=payload.handoff.model_dump(by_alias=True, mode="json"),
        )
        self.session.add(agent)
        try:
            await self.session.flush()
            agent.tools = self._merge_tools(agent, payload.tools)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(f"Agent {payload.name} already exists")
        await self.session.refresh(agent)
        return self._read(agent)

    async def update(self, agent_id: str, payload: AgentUpdate) -> AgentRead:
        agent = await self._get(agent_id)
        fields = payload.model_dump(exclude_unset=True)

        if "tools" in fields:
            fields.pop("tools")
            agent.tools = self._merge_tools(agent, payload.tools or [])
        if "handoff" in fields:
            fields["handoff"] = payload.handoff.model_dump(by_alias=True, mode="json")
        for field, value in fields.items():
            setattr(agent, field, value)

        await self.session.commit()
        await self.session.refresh(agent)
        return self._read(agent)

    async def list(self) -> list[AgentSummary]:
        rows = (
            await self.session.execute(select(Agent).order_by(Agent.created_at))
        ).scalars().all()
        return [self._summary(a) for a in rows]

    async def get(self, agent_id: str) -> AgentRead:
        return self._read(await self._get(agent_id))

    async def set_entrypoint(self, agent_id: str) -> AgentRead:
        """Make this agent the one the runtime starts from, demoting the
        previous entrypoint. Cleared first so the partial unique index never
        sees two."""
        agent = await self._get(agent_id)
        await self.session.execute(
            update(Agent).where(Agent.is_entrypoint).values(is_entrypoint=False)
        )
        await self.session.flush()
        agent.is_entrypoint = True
        await self.session.commit()
        await self.session.refresh(agent)
        return self._read(agent)

    async def delete(self, agent_id: str) -> None:
        await self.session.delete(await self._get(agent_id))
        await self.session.commit()

    async def auth_token_of(self, agent_id: str, tool_name: str) -> str | None:
        """Plaintext auth token, for the caller that makes the outbound call."""
        agent = await self._get(agent_id)
        tool = next((t for t in agent.tools if t["name"] == tool_name), None)
        if tool is None:
            raise NotFoundError(f"Tool {tool_name} not found on agent {agent_id}")
        if not tool.get(_CT) or agent.tools_dek is None:
            return None
        return decrypt_secret(
            base64.b64decode(tool[_CT]), agent.tools_dek, self._aad(agent.id, tool_name)
        )

    async def test_tool(self, agent_id: str, payload: ToolTestRequest) -> ToolTestResult:
        """Run one tool against its real endpoint. A tool edited but not yet
        saved is fine — only the token falls back to what is stored."""
        await self._get(agent_id)
        token = payload.tool.auth_token
        if token is None:
            try:
                token = await self.auth_token_of(agent_id, payload.tool.name)
            except NotFoundError:
                token = None  # the tool is not saved yet, so nothing is stored
        return await tool_runner.run(payload.tool, payload.params, token)

    def _merge_tools(self, agent: Agent, incoming: list[ToolWrite]) -> list[dict[str, Any]]:
        """Whole-list write keyed by tool name: a name that is not sent is
        dropped, and a tool that arrives without `authToken` keeps its stored
        ciphertext."""
        stored = {t["name"]: t for t in (agent.tools or [])}
        merged: list[dict[str, Any]] = []
        for tool in incoming:
            row = tool.model_dump(by_alias=True, mode="json", exclude={"auth_token"})
            previous = stored.get(tool.name, {}).get(_CT)
            if tool.auth is AuthKind.NONE:
                ciphertext = None
            elif tool.auth_token is not None:
                sealed, agent.tools_dek = encrypt_secret(
                    tool.auth_token, self._aad(agent.id, tool.name), agent.tools_dek
                )
                ciphertext = base64.b64encode(sealed).decode()
            else:
                ciphertext = previous
            row[_CT] = ciphertext
            merged.append(row)
        return merged

    @staticmethod
    def _aad(agent_id: str, tool_name: str) -> str:
        return f"{agent_id}:{tool_name}"

    async def _get(self, agent_id: str) -> Agent:
        agent = await self.session.get(Agent, agent_id)
        if agent is None:
            raise NotFoundError(f"Agent {agent_id} not found")
        return agent

    @staticmethod
    def _summary(agent: Agent) -> AgentSummary:
        handoff = Handoff(**agent.handoff)
        return AgentSummary(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            is_entrypoint=agent.is_entrypoint,
            handoff_mode=handoff.mode,
            enabled_tool_count=sum(1 for t in (agent.tools or []) if t.get("enabled")),
            handoff_count=len(handoff.targets),
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )

    def _read(self, agent: Agent) -> AgentRead:
        tools = [
            ToolRead(**{k: v for k, v in t.items() if k != _CT}, has_auth_token=bool(t.get(_CT)))
            for t in (agent.tools or [])
        ]
        return AgentRead(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            instruction=agent.instruction,
            model_id=agent.model_id,
            temperature=agent.temperature,
            knowledge_id=agent.knowledge_id,
            max_step=agent.max_step,
            tools=tools,
            handoff=Handoff(**agent.handoff),
            is_entrypoint=agent.is_entrypoint,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )
