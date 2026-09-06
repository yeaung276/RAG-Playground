from fastapi import Depends, HTTPException, Request

from app.config import get_settings
from app.dependencies.services import get_admin_service
from app.models.admin import Admin
from app.services.admin.admin_service import AdminService
from app.utils.token import verify_token


async def require_admin(
    request: Request,
    svc: AdminService = Depends(get_admin_service),
) -> Admin:
    settings = get_settings()
    token = request.cookies.get(settings.ADMIN_COOKIE_NAME)
    admin_id = (
        verify_token(token, settings.ADMIN_SECRET_KEY, settings.ADMIN_SESSION_HOURS * 3600)
        if token
        else None
    )
    if not admin_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    admin = await svc.get(admin_id)
    if admin is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return admin
