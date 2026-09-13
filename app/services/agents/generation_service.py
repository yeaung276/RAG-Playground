import asyncio
import re
from collections.abc import AsyncIterator
from functools import wraps
from typing import Annotated, Any

from langchain.agents import AgentState, create_agent
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, StructuredTool
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.langgraph import LGManager
from app.logger import get_logger
from app.metrics import generation_duration_seconds, generation_requests_total
from app.models.agent import Agent
from app.models.model import Model
from app.schemas.agent import AgentRead, AgentSummary, HandoffMode, ToolTestResult, ToolWrite
from app.schemas.messages import (
    MessageFrame,
    ThinkingFrame,
    TokenFrame,
    ToolCallFrame,
    ToolResultFrame,
)
from app.schemas.model import Capability
from app.services.agents import tool_runner
from app.services.agents.agent_service import AgentService
from app.services.agents.middleware import max_step, transfer_alone
from app.services.utils.messages import thinking
from app.services.errors import ConflictError
from app.services.model_service import ModelService


logger = get_logger(__name__)


class GenerationService:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession], langgraph: LGManager):
        self.session_maker = session_maker
        self.langgraph = langgraph

    @staticmethod
    def _track(stream):
        @wraps(stream)
        async def wrapper(*args, **kwargs):
            with (
                generation_duration_seconds.time(),
                generation_requests_total.labels(status="error").count_exceptions(),
            ):
                async for frame in stream(*args, **kwargs):
                    yield frame
            generation_requests_total.labels(status="success").inc()

        return wrapper

    @_track
    async def stream_reply(
        self, session_id: str, message: str | None = None
    ) -> AsyncIterator[
        TokenFrame | ThinkingFrame | ToolCallFrame | ToolResultFrame | MessageFrame
    ]:
        """Yields the agent's reply one frame at a time. The thread is the chat
        session, so the checkpointer resumes where the last turn ended."""
        graph = await self.assemble_graph()

        async for namespace, mode, data in graph.astream(
            {"messages": [HumanMessage(message or "")]},
            config={"configurable": {"thread_id": session_id}},
            stream_mode=["messages", "updates"],
            subgraphs=True,
        ):
            if not namespace:
                continue
            agent = namespace[0].split(":")[0]

            if mode == "messages":
                chunk, _ = data
                if not isinstance(chunk, AIMessageChunk):
                    continue
                if thought := thinking(chunk):
                    yield ThinkingFrame(agent=agent, delta=thought)
                if chunk.text:
                    yield TokenFrame(agent=agent, delta=chunk.text)
                for call in chunk.tool_call_chunks:
                    if call["name"]:
                        yield ToolCallFrame(name=call["name"])
                continue

            for update in (data or {}).values():
                if not isinstance(update, dict):
                    continue
                for msg in update.get("messages") or []:
                    if isinstance(msg, AIMessage):
                        yield MessageFrame(
                            agent=agent,
                            role="ai",
                            content=msg.text,
                            thinking=thinking(msg) or None,
                            usage=msg.usage_metadata,
                        )
                    elif isinstance(msg, ToolMessage):
                        yield ToolResultFrame(
                            agent=agent,
                            name=msg.name,
                            args=getattr(msg.artifact, "args", {}),
                            content=msg.text,
                            status="error" if msg.status == "error" else "success",
                            elapsed_ms=getattr(msg.artifact, "elapsed_ms", None),
                        )

    async def assemble_graph(self) -> CompiledStateGraph:
        async def loader() -> StateGraph:
            async with self.session_maker() as session:
                service = AgentService(session)
                roster = await service.list()
                agents = [await service.get(a.id) for a in roster]

            entry = next((a for a in agents if a.is_entrypoint), None)
            if entry is None:
                raise ConflictError("No entrypoint agent is set")

            graph = StateGraph(AgentState)
            for agent in agents:
                graph.add_node(agent.name, await self._create_agent_node(agent, roster))
                graph.add_edge(agent.name, END)
            graph.set_entry_point(entry.name)
            return graph

        return await self.langgraph.get_or_create(await self._stamp(), loader)

    async def _stamp(self) -> dict[str, Any]:
        async with self.session_maker() as session:
            agents = await session.execute(
                select(func.count(Agent.id), func.max(Agent.updated_at))
            )
            models = await session.execute(
                select(func.count(Model.id), func.max(Model.updated_at))
            )
        return {"agents": agents.one(), "models": models.one()}

    async def _create_agent_node(
        self, agent: AgentRead, roster: list[AgentSummary]
    ) -> CompiledStateGraph:
        defaults = await self._create_default_tools(agent)
        tools = await self._create_agent_tools(agent)
        handoffs = await self._create_agent_handoffs(agent, roster)
        return create_agent(
            model=await self._resolve_llm(agent.model_id, agent.temperature),
            tools=defaults + tools + handoffs,
            system_prompt=agent.instruction,
            middleware=[
                max_step(agent.max_step),
                transfer_alone({t.name for t in handoffs}),
            ],
            name=agent.name,
        )
    
    async def _resolve_llm(self, model_id: str | None, temperature: int = 0) -> BaseChatModel:
        if model_id is None:
            raise ConflictError("Agent has no model assigned")

        async with self.session_maker() as session:
            models = ModelService(session)
            model = await models.get(model_id)
            if model.capability is not Capability.DECODER:
                raise ConflictError(f"{model.name} is a {model.capability} model, not a decoder")
            api_key = await models.api_key_of(model_id)

        logger.info(
            "resolving llm name=%s schema=%s base_url=%s",
            model.name,
            model.api_schema,
            model.base_url,
        )
        return init_chat_model(
            model.name,
            model_provider=model.api_schema,
            base_url=model.base_url,
            api_key=api_key,
            temperature=temperature / 50,
        )
        
    async def _create_agent_tools(self, agent: AgentRead) -> list[BaseTool]:
        enabled = [t for t in agent.tools if t.enabled]
        async with self.session_maker() as session:
            agents = AgentService(session)
            tokens = {t.name: await agents.auth_token_of(agent.id, t.name) for t in enabled}

        tools: list[BaseTool] = []
        for spec in enabled:
            call = ToolWrite(**spec.model_dump(exclude={"has_auth_token"}))
            token = tokens[spec.name]

            async def run(_call=call, _token=token, **params) -> tuple[str, ToolTestResult]:
                result = await tool_runner.run(_call, params, _token)
                return result.error or result.body, result

            tools.append(
                StructuredTool.from_function(
                    coroutine=run,
                    name=spec.name,
                    description=spec.description,
                    args_schema=tool_runner.args_schema(spec),
                    response_format="content_and_artifact",
                )
            )
        return tools
        
    async def _create_default_tools(self, agent: AgentRead) -> list[BaseTool]:
        # TODO: bind the knowledge base retrieval tool when agent.knowledge_id is set
        return []

    async def _create_agent_handoffs(
        self, agent: AgentRead, roster: list[AgentSummary]
    ) -> list[BaseTool]:
        """One transfer tool per agent this one may hand off to. Calling it
        routes the parent graph to that agent's node."""
        others = {a.id: a for a in roster if a.id != agent.id}
        match agent.handoff.mode:
            case HandoffMode.NONE:
                return []
            case HandoffMode.AUTO:
                targets = [(a, a.description) for a in others.values()]
            case HandoffMode.MANUAL:
                targets = [
                    (others[t.agent_id], t.description or others[t.agent_id].description)
                    for t in agent.handoff.targets
                    if t.agent_id in others
                ]

        def transfer_tool(name: str, description: str) -> BaseTool:
            """Closed over its one target, so the model only chooses which tool
            to call and cannot redirect the handoff."""

            def transfer(tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
                return Command(
                    goto=name,
                    graph=Command.PARENT,
                    update={
                        "messages": [
                            ToolMessage(content=f"Handed off to {name}", tool_call_id=tool_call_id)
                        ]
                    },
                )

            return StructuredTool.from_function(
                func=transfer,
                name=f"transfer_to_{re.sub(r'[^a-zA-Z0-9_.:-]', '_', name)}",
                description=f"Hand the conversation to {name}. {description}",
            )

        return [transfer_tool(t.name, d) for t, d in targets]