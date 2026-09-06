from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.responses import Response

from app.backgrounds.files_processor import FileProcessor
from app.dependencies.services import get_file_processor, get_file_service
from app.schemas.knowledge import (
    FileDetail,
    FolderCreate,
    NodeRead,
)
from app.services.knowledge.file_service import FileService

router = APIRouter(prefix="/knowledge", tags=["files"])


@router.post("/{kb_id}/folders", response_model=NodeRead, status_code=201)
async def create_folder(
    kb_id: str, payload: FolderCreate, svc: FileService = Depends(get_file_service)
):
    return await svc.create_folder(kb_id, payload.parent_id, payload.name)


@router.post("/{kb_id}/files", response_model=list[NodeRead], status_code=201)
async def upload_files(
    kb_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    parent: str | None = None,
    svc: FileService = Depends(get_file_service),
    processor: FileProcessor = Depends(get_file_processor),
):
    nodes = await svc.upload_files(kb_id, parent, files)
    for node in nodes:
        background_tasks.add_task(processor.process, node.id)
    return nodes


@router.get("/{kb_id}/nodes", response_model=list[NodeRead])
async def list_nodes(
    kb_id: str,
    parent: str | None = None,
    svc: FileService = Depends(get_file_service),
):
    return await svc.list_nodes(kb_id, parent)


@router.get("/{kb_id}/files/{node_id}", response_model=FileDetail)
async def get_file_detail(
    kb_id: str, node_id: str, svc: FileService = Depends(get_file_service)
):
    return await svc.get_file_detail(kb_id, node_id)


@router.get("/{kb_id}/files/{node_id}/download")
async def download_file(
    kb_id: str, node_id: str, svc: FileService = Depends(get_file_service)
):
    name, mime, data = await svc.read_file(kb_id, node_id)
    disposition = f"attachment; filename*=UTF-8''{quote(name)}"
    return Response(
        content=data, media_type=mime, headers={"Content-Disposition": disposition}
    )


@router.post("/{kb_id}/files/{node_id}/resync", response_model=NodeRead)
async def resync_file(
    kb_id: str,
    node_id: str,
    background_tasks: BackgroundTasks,
    svc: FileService = Depends(get_file_service),
    processor: FileProcessor = Depends(get_file_processor),
):
    node = await svc.resync_node(kb_id, node_id)
    background_tasks.add_task(processor.process, node.id)
    return node


@router.delete("/{kb_id}/nodes/{node_id}", status_code=204)
async def delete_node(
    kb_id: str,
    node_id: str,
    background_tasks: BackgroundTasks,
    svc: FileService = Depends(get_file_service),
    processor: FileProcessor = Depends(get_file_processor),
):
    storage_keys = await svc.delete_node(kb_id, node_id)
    if storage_keys:
        background_tasks.add_task(processor.delete, storage_keys)
    return Response(status_code=204)
