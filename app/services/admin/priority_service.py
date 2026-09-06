from collections.abc import Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.message import Message
from app.models.session import Session
from app.services.realtime import ADMIN_DIRTY, ADMIN_NOTI_CHANNEL, Event, Publisher


W_DOWNVOTE = 100
W_UPVOTE = 50
W_CANNOT_ANSWER = 40
SMOOTHING = 2

# status_flags is the "attention accumulator since last admin visit" (distinct
# from sessions.upvotes/downvotes, which are lifetime tallies). Reset on visit.
EMPTY_FLAGS: dict[str, Any] = {
    "upvote_count": 0,
    "downvote_count": 0,
    "agent_cannot_answer": False,
}


class PriorityService:
    """Owns priority scoring and the admin attention/history lists. Callers only
    mutate flags via bump()/clear(); scoring lives here in one place."""

    def __init__(self, db: AsyncSession, publisher: Publisher | None = None):
        self._db = db
        self._publisher = publisher

    @classmethod
    @asynccontextmanager
    async def from_session_maker(
        cls, session_maker: async_sessionmaker, publisher: Publisher | None = None
    ):
        """For use outside a request/DI scope (e.g. the chat send flow around the
        long generation call): opens its own short-lived session."""
        async with session_maker() as db:
            yield cls(db, publisher if publisher is not None else Publisher(db))

    @staticmethod
    def _score(flags: dict[str, Any], message_count: int) -> int:
        n = message_count + SMOOTHING
        down = flags.get("downvote_count", 0) or 0
        up = flags.get("upvote_count", 0) or 0
        stuck = 1 if flags.get("agent_cannot_answer") else 0
        raw = W_DOWNVOTE * (down / n) - W_UPVOTE * (up / n) + W_CANNOT_ANSWER * stuck
        return max(0, min(100, round(raw)))

    async def bump(
        self,
        session_id: str,
        *,
        upvote_delta: int = 0,
        downvote_delta: int = 0,
        cannot_answer: bool | None = None,
    ) -> None:
        """Move the attention accumulator and rescore. All status_flags mutation
        goes through here so the read-modify-write stays in one place."""

        def mutate(flags: dict[str, Any]) -> None:
            if upvote_delta:
                flags["upvote_count"] = max(0, flags["upvote_count"] + upvote_delta)
            if downvote_delta:
                flags["downvote_count"] = max(0, flags["downvote_count"] + downvote_delta)
            if cannot_answer is not None:
                flags["agent_cannot_answer"] = cannot_answer

        await self._rescore(session_id, mutate)

    async def clear(self, session_id: str) -> None:
        """Reset the accumulator (when an admin visits/intercepts) and rescore, so a
        handled conversation drops back down."""
        await self._rescore(session_id, lambda flags: flags.update(EMPTY_FLAGS))

    async def _rescore(self, session_id: str, mutate) -> None:
        session = await self._db.get(Session, session_id, with_for_update=True)
        if session is None:
            return
        flags = {**EMPTY_FLAGS, **(session.status_flags or {})}
        mutate(flags)
        count = await self._db.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.session_id == session_id)
        )
        trigger_message = await self._db.scalar(
            select(Message.content)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        session.status_flags = flags
        session.priority = self._score(flags, count or 0)
        session.trigger_message = trigger_message
        if self._publisher is not None:
            await self._publisher.publish(
                ADMIN_NOTI_CHANNEL, "", Event(type=ADMIN_DIRTY)
            )
        await self._db.commit()

    async def list_current(
        self,
        *,
        page: int,
        page_size: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[Sequence[Session], int]:
        """The live attention feed: online, not currently being handled, ranked by
        priority then longest-waiting (FIFO) within a band."""
        stmt = select(Session).where(
            Session.status == "active", Session.intercepted.is_(False)
        )
        stmt = self._apply_dates(stmt, date_from, date_to)
        total = await self._count(stmt)
        stmt = (
            stmt.order_by(desc(Session.priority), asc(Session.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self._db.execute(stmt)).scalars().all()
        return rows, total

    @staticmethod
    def _apply_dates(stmt, date_from: datetime | None, date_to: datetime | None):
        if date_from is not None:
            stmt = stmt.where(Session.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(Session.created_at <= date_to)
        return stmt

    async def _count(self, stmt) -> int:
        total = await self._db.scalar(
            select(func.count()).select_from(stmt.subquery())
        )
        return total or 0