import uuid
from collections.abc import AsyncIterator
from datetime import timedelta

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.logger import get_logger
from app.config import get_settings
from app.models.message import Message
from app.models.session import Session
from app.services.realtime import CHAT_CHANNEL, Event, PubSub

logger = get_logger("services.session")


class SessionService:
    """Session DB CRUD plus chat-stream subscription. Owns the chat-domain topic
    convention (a session's events live on CHAT_CHANNEL under topic=session_id);
    the shared listen connection itself belongs to PubSub."""

    def __init__(self, sessionmaker: async_sessionmaker, pubsub: PubSub | None = None):
        # Unlike MessageService (which takes a live AsyncSession), this service
        # takes a sessionmaker and opens a short session per method. That's
        # deliberate: nearly every caller is long-lived or streaming (widget/admin
        # SSE, the ~40s chat-send request), where a request-scoped db would pin a
        # pooled connection for the whole stream/request. Per-method sessions keep
        # nothing pinned. `pubsub` is optional so CRUD-only construction (tests,
        # background tasks) doesn't require it; subscribe() asserts it's present.
        self._sessionmaker = sessionmaker
        self._pubsub = pubsub

    def subscribe(self, session_id: str) -> AsyncIterator[Event]:
        assert self._pubsub is not None, "SessionService constructed without PubSub"
        return self._pubsub.subscribe(CHAT_CHANNEL, session_id)

    async def create(self) -> Session:
        async with self._sessionmaker() as db:
            session = Session(id=str(uuid.uuid4()), status="active")
            db.add(session)
            await db.commit()
            await db.refresh(session)
        logger.info("session opened (id: %s)", session.id)
        return session

    async def get_or_create(self, session_id: str, status: str = "disconnected") -> Session:
        async with self._sessionmaker() as db:
            session = await db.get(Session, session_id)
            if session is None:
                session = Session(id=session_id, status=status)
                db.add(session)
                await db.commit()
                logger.info("session opened (id: %s)", session_id)
        return session

    async def get_active(self, session_id: str) -> Session | None:
        timeout = timedelta(minutes=get_settings().SESSION_TIMEOUT_MINUTES)
        async with self._sessionmaker() as db:
            result = await db.execute(
                select(Session).where(
                    Session.id == session_id,
                    or_(
                        Session.status == "active",
                        and_(
                            Session.status == "disconnected",
                            Session.disconnected_at > func.now() - timeout,
                        ),
                    ),
                )
            )
            return result.scalar_one_or_none()

    async def disconnect(self, session_id: str) -> None:
        async with self._sessionmaker() as db:
            await db.execute(
                update(Session)
                .where(Session.id == session_id, Session.status == "active")
                .values(status="disconnected", disconnected_at=func.now())
            )
            await db.commit()
        logger.info("session disconnected (id: %s)", session_id)

    async def reconcile_stale_status(self, session_id: str) -> None:
        timeout = timedelta(minutes=get_settings().SESSION_TIMEOUT_MINUTES)
        last_message_at = (
            select(func.max(Message.created_at))
            .where(Message.session_id == session_id)
            .scalar_subquery()
        )
        last_activity_at = func.coalesce(last_message_at, Session.created_at)
        async with self._sessionmaker() as db:
            result = await db.execute(
                update(Session)
                .where(
                    Session.id == session_id,
                    Session.status == "active",
                    last_activity_at < func.now() - timeout,
                )
                .values(status="disconnected", disconnected_at=func.now())
            )
            await db.commit()
        if result.rowcount:
            logger.info("stale session disconnected (id: %s)", session_id)

    async def reconnect(self, session_id: str) -> Session | None:
        session = await self.get_active(session_id)
        if session is None:
            return None
        async with self._sessionmaker() as db:
            await db.execute(
                update(Session)
                .where(Session.id == session_id)
                .values(status="active", disconnected_at=None)
            )
            await db.commit()
        logger.info("session reconnected (id: %s)", session_id)
        return session

    async def is_intercepted(self, session_id: str) -> bool:
        async with self._sessionmaker() as db:
            return bool(
                await db.scalar(
                    select(Session.intercepted).where(Session.id == session_id)
                )
            )

    async def intercept(self, session_id: str, admin_id: str) -> None:
        async with self._sessionmaker() as db:
            await db.execute(
                update(Session)
                .where(Session.id == session_id)
                .values(
                    intercepted=True,
                    last_intercepted_by=admin_id,
                    last_intercepted_at=func.now(),
                )
            )
            await db.commit()
        logger.info("session intercepted (id: %s, admin: %s)", session_id, admin_id)

    async def release(self, session_id: str) -> None:
        # Leave last_intercepted_* in place as the audit trail of who last took over.
        async with self._sessionmaker() as db:
            await db.execute(
                update(Session)
                .where(Session.id == session_id)
                .values(intercepted=False)
            )
            await db.commit()
        logger.info("session released (id: %s)", session_id)
