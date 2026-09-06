from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session


class AdminSessionService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def list_history(
        self,
        *,
        page: int,
        page_size: int,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> tuple[Sequence[Session], int]:
        """All sessions, newest first, for the history tab. The live attention
        feed (current view) lives in PriorityService."""
        stmt = select(Session)

        if date_from is not None:
            stmt = stmt.where(Session.created_at >= date_from)

        if date_to is not None:
            stmt = stmt.where(Session.created_at <= date_to)

        total = await self._db.scalar(select(func.count()).select_from(stmt.subquery()))

        stmt = (
            stmt.order_by(desc(Session.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self._db.execute(stmt)).scalars().all()
        return rows, total or 0