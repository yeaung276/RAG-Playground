import uuid
from contextlib import asynccontextmanager

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.message import Message
from app.models.session import Session
from app.schemas.messages import FeedbackEventData
from app.services.errors import NotFoundError
from app.services.realtime import (
    CHAT_CHANNEL,
    FEEDBACK_UPDATED,
    MESSAGE_CREATED,
    Event,
    Publisher,
)


class MessageService:
    def __init__(self, db: AsyncSession, publisher: Publisher | None = None):
        self._db = db
        self._publisher = publisher

    @classmethod
    @asynccontextmanager
    async def from_session_maker(
        cls, session_maker: async_sessionmaker, publisher: Publisher | None = None
    ):
        """For use outside a request/DI scope (e.g. the chat send flow around the
        long generation call): opens its own short-lived
        session and wires a Publisher on it, so no connection is held between
        creates."""
        async with session_maker() as db:
            yield cls(db, publisher if publisher is not None else Publisher(db))

    async def create(
        self,
        session_id: str,
        sender: str,
        content: str | None,
        has_image: bool = False,
        publish: bool = True,
    ) -> Message:
        message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            sender=sender,
            content=content,
            has_image=has_image,
        )
        self._db.add(message)
        await self._db.flush()
        await self._db.refresh(message)
        if publish and self._publisher is not None:
            await self._publisher.publish(
                CHAT_CHANNEL,
                session_id,
                Event(
                    type=MESSAGE_CREATED,
                    session_id=session_id,
                    data={"id": message.id},
                ),
            )
        await self._db.commit()
        return message

    async def set_feedback(
        self, session_id: str, message_id: str, value: str | None
    ) -> Message:
        message = await self._db.scalar(
            select(Message)
            .where(Message.id == message_id, Message.session_id == session_id)
            .with_for_update()
        )
        if message is None:
            raise NotFoundError(f"Message {message_id} not found")

        old = message.feedback
        if old == value:
            return message

        up = (value == "like") - (old == "like")
        down = (value == "dislike") - (old == "dislike")
        message.feedback = value
        if up or down:
            await self._db.execute(
                update(Session)
                .where(Session.id == session_id)
                .values(
                    upvotes=Session.upvotes + up,
                    downvotes=Session.downvotes + down,
                )
            )
        if self._publisher is not None:
            await self._publisher.publish(
                CHAT_CHANNEL,
                session_id,
                Event(
                    type=FEEDBACK_UPDATED,
                    session_id=session_id,
                    data=FeedbackEventData(id=message.id, feedback=value).model_dump(
                        mode="json", by_alias=True
                    ),
                ),
            )
        await self._db.commit()
        await self._db.refresh(message)
        return message

    async def get(self, session_id: str, message_id: str) -> Message | None:
        return await self._db.scalar(
            select(Message).where(
                Message.id == message_id, Message.session_id == session_id
            )
        )

    async def list(self, session_id: str, limit: int = 20) -> list[Message]:
        # Keep only the newest `limit` messages (order desc + limit), then flip
        # back to chronological order for rendering. No pagination: older
        # messages beyond the cap are silently discarded (assumed rare).
        if await self._db.get(Session, session_id) is None:
            raise NotFoundError(f"Session {session_id} not found")

        result = await self._db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())[::-1]
