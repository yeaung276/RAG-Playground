from fastapi import APIRouter, Depends

from app.dependencies.services import get_kb_service
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
)
from app.services.knowledge.kb_service import KnowledgeBaseService

router = APIRouter(prefix="/knowledge", tags=["knowledge-bases"])


@router.post("", response_model=KnowledgeBaseRead, status_code=201)
async def create_base(
    payload: KnowledgeBaseCreate,
    svc: KnowledgeBaseService = Depends(get_kb_service),
):
    return await svc.create(payload.name, payload.config)


@router.patch("/{kb_id}", response_model=KnowledgeBaseRead)
async def update_base(
    kb_id: str,
    payload: KnowledgeBaseUpdate,
    svc: KnowledgeBaseService = Depends(get_kb_service),
):
    return await svc.update_config(kb_id, payload.config)


@router.get("", response_model=list[KnowledgeBaseRead])
async def list_bases(svc: KnowledgeBaseService = Depends(get_kb_service)):
    return await svc.list()


@router.get("/{kb_id}", response_model=KnowledgeBaseRead)
async def get_base(kb_id: str, svc: KnowledgeBaseService = Depends(get_kb_service)):
    return await svc.get(kb_id)
