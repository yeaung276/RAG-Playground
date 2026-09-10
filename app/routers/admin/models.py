from fastapi import APIRouter, Depends, Query

from app.dependencies.services import get_model_service
from app.schemas.model import Capability, ModelCreate, ModelPage, ModelRead, ModelUpdate
from app.services.model_service import ModelService

router = APIRouter(prefix="/models", tags=["models"])


@router.post("", response_model=ModelRead, status_code=201)
async def create_model(
    payload: ModelCreate,
    svc: ModelService = Depends(get_model_service),
):
    return await svc.create(payload)


@router.get("", response_model=ModelPage)
async def list_models(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    capability: Capability | None = Query(None),
    svc: ModelService = Depends(get_model_service),
):
    return await svc.list(page=page, page_size=page_size, capability=capability)


@router.get("/{model_id}", response_model=ModelRead)
async def get_model(model_id: str, svc: ModelService = Depends(get_model_service)):
    return await svc.get(model_id)


@router.patch("/{model_id}", response_model=ModelRead)
async def update_model(
    model_id: str,
    payload: ModelUpdate,
    svc: ModelService = Depends(get_model_service),
):
    return await svc.update(model_id, payload)


@router.delete("/{model_id}", status_code=204)
async def delete_model(model_id: str, svc: ModelService = Depends(get_model_service)):
    await svc.delete(model_id)
