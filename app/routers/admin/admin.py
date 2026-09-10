from fastapi import APIRouter, Depends

from app.dependencies.admin import require_admin
from app.routers.admin import agents, auth, chat, files, kb, models, notifications


router = APIRouter(prefix="/api/admin", tags=["admin"])

router.include_router(auth.router)
router.include_router(agents.router, dependencies=[Depends(require_admin)])
router.include_router(chat.router, dependencies=[Depends(require_admin)])
router.include_router(files.router, dependencies=[Depends(require_admin)])
router.include_router(kb.router, dependencies=[Depends(require_admin)])
router.include_router(models.router, dependencies=[Depends(require_admin)])
router.include_router(notifications.router, dependencies=[Depends(require_admin)])