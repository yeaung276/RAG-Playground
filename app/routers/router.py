from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.dependencies.guards import dev_only
from app.routers import chat, control, admin

# Aggregates the per-resource routers; included by main.py.
router = APIRouter()
router.include_router(chat.router)
router.include_router(control.router)
router.include_router(admin.router)

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/dev", dependencies=[Depends(dev_only)])
async def dev_page():
    return FileResponse("app/templates/demo.html", media_type="text/html")