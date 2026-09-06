import asyncio
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.db.session import async_session_maker
from app.dependencies.admin import require_admin
from app.dependencies.services import (
    get_admin_session_service,
    get_hydrator,
    get_message_service,
    get_priority_service,
    get_session_service,
)
from app.models.admin import Admin
from app.schemas.admin import AdminChatSessionPage, AdminMessage
from app.schemas.messages import ChatResponse
from app.services.admin.admin_session_service import AdminSessionService
from app.services.admin.priority_service import PriorityService
from app.services.chat.message_service import MessageService
from app.services.chat.session_service import SessionService
from app.services.hydrator import Hydrator

router = APIRouter(prefix="/chats", tags=["admin-chats"])


@router.get("/current", response_model=AdminChatSessionPage)
async def list_current(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    date_from: datetime | None = Query(None, alias="from"),
    date_to: datetime | None = Query(None, alias="to"),
    svc: PriorityService = Depends(get_priority_service),
):
    rows, total = await svc.list_current(
        page=page, page_size=page_size, date_from=date_from, date_to=date_to
    )
    return AdminChatSessionPage(items=rows, total=total, page=page, page_size=page_size)


@router.get("/history", response_model=AdminChatSessionPage)
async def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    date_from: datetime | None = Query(None, alias="from"),
    date_to: datetime | None = Query(None, alias="to"),
    svc: AdminSessionService = Depends(get_admin_session_service),
):
    rows, total = await svc.list_history(
        page=page, page_size=page_size, date_from=date_from, date_to=date_to
    )
    return AdminChatSessionPage(items=rows, total=total, page=page, page_size=page_size)

@router.get("/{session_id}/messages", response_model=list[ChatResponse])
async def get_messages(
    session_id: str,
    svc: MessageService = Depends(get_message_service),
):
    return await svc.list(session_id)

@router.post("/{session_id}/messages", response_model=ChatResponse)
async def send_message(
    session_id: str,
    request: AdminMessage,
    admin: Admin = Depends(require_admin),
    messages: MessageService = Depends(get_message_service),
):
    return await messages.create(
        session_id, get_settings().AGENT_NAME, request.content
    )

@router.post("/{session_id}/intercept")
async def intercept_session(
    session_id: str,
    mode: Literal["intercept", "audit"] = "audit",
    admin: Admin = Depends(require_admin),
    sessions: SessionService = Depends(get_session_service),
    hydrator: Hydrator = Depends(get_hydrator),
):
    await sessions.reconcile_stale_status(session_id)

    if mode == "intercept":
        await sessions.intercept(session_id, admin.id)

        async with PriorityService.from_session_maker(async_session_maker) as priority:
            await priority.clear(session_id)
        
        async with MessageService.from_session_maker(async_session_maker) as messages:
            await messages.create(session_id, "system", "Admin joined the chat")

    async def leave() -> None:
        await sessions.release(session_id)
        async with MessageService.from_session_maker(async_session_maker) as messages:
            await messages.create(session_id, "system", "Admin left the chat")

    async def stream():
        try:
            yield ": connected\n\n"
            async for event in sessions.subscribe(session_id):
                frame = await hydrator.hydrate(event)
                if frame is None:
                    continue
                yield f"data: {frame.model_dump_json(by_alias=True)}\n\n"
        finally:
            if mode == "intercept":
                await asyncio.shield(leave())

    return StreamingResponse(stream(), media_type="text/event-stream")