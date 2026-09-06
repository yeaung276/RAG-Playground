import asyncio

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.logger import get_logger
from app.services.chat.session_service import SessionService
from app.services.hydrator import Hydrator
from app.dependencies.services import get_hydrator, get_session_service
from app.dependencies.session import get_session

logger = get_logger("routers.control")

router = APIRouter(prefix="/api", tags=["control"])


@router.post("/control")
async def control(
    new: bool = False,
    session_id: str | None = Depends(get_session),
    sessions: SessionService = Depends(get_session_service),
    hydrator: Hydrator = Depends(get_hydrator),
):
    settings = get_settings()
    session = None

    if session_id and not new:
        session = await sessions.reconnect(session_id)
    if session is None:
        session = await sessions.create()

    async def stream():
        logger.info("control stream opened (session: %s)", session.id)
        try:
            yield ": connected\n\n"
            async for event in sessions.subscribe(session.id):
                frame = await hydrator.hydrate(event)
                if frame is None:
                    continue
                yield f"data: {frame.model_dump_json(by_alias=True)}\n\n"
        finally:
            logger.info("control stream closed (session: %s)", session.id)
            await asyncio.shield(sessions.disconnect(session.id))

    response = StreamingResponse(stream(), media_type="text/event-stream")
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session.id,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,  # pyright: ignore[reportArgumentType]
        path="/",
    )
    return response
