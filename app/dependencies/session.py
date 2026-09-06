from fastapi import Depends, HTTPException, Request

from app.config import get_settings
from app.services.chat.session_service import SessionService
from app.dependencies.services import get_session_service


async def require_session(
    request: Request,
    sessions: SessionService = Depends(get_session_service),
) -> str:
    settings = get_settings()
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_id:
        raise HTTPException(status_code=401, detail="Missing session")
    session = await sessions.reconnect(session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session_id


def get_session(request: Request) -> str | None:
    return request.cookies.get(get_settings().SESSION_COOKIE_NAME)
