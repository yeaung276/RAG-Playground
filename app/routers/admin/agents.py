from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies.services import get_agent_service, get_generation_service
from app.schemas.agent import (
    AgentCreate,
    AgentRead,
    AgentSummary,
    AgentTestRequest,
    AgentUpdate,
    ToolTestRequest,
    ToolTestResult,
)
from app.schemas.messages import DoneFrame, ErrorFrame
from app.services.agents.agent_service import AgentService
from app.services.agents.generation_service import GenerationService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentRead, status_code=201)
async def create_agent(
    payload: AgentCreate,
    svc: AgentService = Depends(get_agent_service),
):
    return await svc.create(payload)


@router.get("", response_model=list[AgentSummary])
async def list_agents(svc: AgentService = Depends(get_agent_service)):
    return await svc.list()


@router.post("/test")
async def test_agents(
    payload: AgentTestRequest,
    generation: GenerationService = Depends(get_generation_service),
):
    async def stream():
        try:
            async for frame in generation.stream_reply(payload.thread_id, payload.message):
                yield f"data: {frame.model_dump_json(by_alias=True)}\n\n"
        except Exception as exc:
            yield f"data: {ErrorFrame(message=str(exc)).model_dump_json(by_alias=True)}\n\n"
        yield f"data: {DoneFrame().model_dump_json(by_alias=True)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(agent_id: str, svc: AgentService = Depends(get_agent_service)):
    return await svc.get(agent_id)


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    svc: AgentService = Depends(get_agent_service),
):
    return await svc.update(agent_id, payload)


@router.post("/{agent_id}/tools/test", response_model=ToolTestResult)
async def test_tool(
    agent_id: str,
    payload: ToolTestRequest,
    svc: AgentService = Depends(get_agent_service),
):
    return await svc.test_tool(agent_id, payload)


@router.put("/{agent_id}/entrypoint", response_model=AgentRead)
async def set_entrypoint(agent_id: str, svc: AgentService = Depends(get_agent_service)):
    return await svc.set_entrypoint(agent_id)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, svc: AgentService = Depends(get_agent_service)):
    await svc.delete(agent_id)
