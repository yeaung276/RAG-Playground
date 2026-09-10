from fastapi import APIRouter, Depends

from app.dependencies.services import get_agent_service
from app.schemas.agent import (
    AgentCreate,
    AgentRead,
    AgentSummary,
    AgentUpdate,
    ToolTestRequest,
    ToolTestResult,
)
from app.services.agents.agent_service import AgentService

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
