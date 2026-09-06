from fastapi import APIRouter, Depends, HTTPException, Response

from app.config import get_settings
from app.dependencies.admin import require_admin
from app.dependencies.services import get_admin_service
from app.models.admin import Admin
from app.schemas.admin import AdminRead, LoginRequest
from app.services.admin.admin_service import AdminService
from app.utils.token import sign_token

router = APIRouter(tags=["admin-auth"])


@router.post("/login", response_model=AdminRead)
async def login(
    payload: LoginRequest,
    response: Response,
    svc: AdminService = Depends(get_admin_service),
):
    admin = await svc.authenticate(payload.username, payload.password)
    if admin is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    settings = get_settings()
    token = sign_token(admin.id, settings.ADMIN_SECRET_KEY)
    response.set_cookie(
        key=settings.ADMIN_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,  # pyright: ignore[reportArgumentType]
        max_age=settings.ADMIN_SESSION_HOURS * 3600,
        path="/",
    )
    return admin


@router.post("/logout", status_code=204)
async def logout():
    resp = Response(status_code=204)
    resp.delete_cookie(get_settings().ADMIN_COOKIE_NAME, path="/")
    return resp


@router.get("/me", response_model=AdminRead)
async def me(admin: Admin = Depends(require_admin)):
    return admin
