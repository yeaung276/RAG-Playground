from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from pydantic import ValidationError

from app.backgrounds.dataset_processor import DatasetProcessor
from app.dependencies.services import get_dataset_processor, get_dataset_service
from app.schemas.dataset import DatasetCreate, DatasetPage, DatasetRead
from app.services.dataset.dataset_service import DatasetService

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetRead, status_code=201)
async def create_dataset(
    background_tasks: BackgroundTasks,
    payload: str = Form(...),  # the form's JSON, alongside the archive part
    archive: UploadFile = File(...),
    svc: DatasetService = Depends(get_dataset_service),
    processor: DatasetProcessor = Depends(get_dataset_processor),
):
    try:
        values = DatasetCreate.model_validate_json(payload)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors())
    dataset = await svc.create(values, archive)
    background_tasks.add_task(processor.generate, dataset.id)
    return dataset


@router.get("", response_model=DatasetPage)
async def list_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    svc: DatasetService = Depends(get_dataset_service),
):
    return await svc.list(page=page, page_size=page_size)


@router.get("/{dataset_id}", response_model=DatasetRead)
async def get_dataset(
    dataset_id: str, svc: DatasetService = Depends(get_dataset_service)
):
    return await svc.get(dataset_id)


@router.get("/{dataset_id}/pairs")
async def get_dataset_pairs(
    dataset_id: str, svc: DatasetService = Depends(get_dataset_service)
):
    name, data = await svc.read_pairs(dataset_id)
    disposition = f"attachment; filename*=UTF-8''{quote(name)}"
    return Response(
        content=data,
        media_type="application/json",
        headers={"Content-Disposition": disposition},
    )
