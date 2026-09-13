from datetime import datetime

import pytest

from app.models.message import Message
from app.models.session import Session
from app.services.errors import NotFoundError
from app.services.chat.message_service import MessageService
from app.services.chat.session_service import SessionService


async def test_create_persists_fields(db_sessionmaker):
    session = await SessionService(db_sessionmaker).create()
    async with db_sessionmaker() as db:
        message = await MessageService(db).create(session.id, "user", None)
    assert message.session_id == session.id
    assert message.sender == "user"
    assert message.content is None


async def test_list_orders_by_created_at(db_sessionmaker):
    session = await SessionService(db_sessionmaker).create()
    async with db_sessionmaker() as db:
        # inserted out of chronological order to prove list() sorts by created_at
        db.add(Message(id="m2", session_id=session.id, sender="agent", content="second", created_at=datetime(2026, 1, 1, 0, 1)))
        db.add(Message(id="m1", session_id=session.id, sender="user", content="first", created_at=datetime(2026, 1, 1, 0, 0)))
        await db.commit()
        rows = await MessageService(db).list(session.id)
    assert [m.id for m in rows] == ["m1", "m2"]


async def test_list_scoped_to_session(db_sessionmaker):
    sessions = SessionService(db_sessionmaker)
    a = await sessions.create()
    b = await sessions.create()
    async with db_sessionmaker() as db:
        svc = MessageService(db)
        await svc.create(a.id, "user", "in-a", False)
        await svc.create(b.id, "user", "in-b", False)
        rows = await svc.list(a.id)
    assert [m.content for m in rows] == ["in-a"]


async def _counters(db_sessionmaker, session_id):
    async with db_sessionmaker() as db:
        s = await db.get(Session, session_id)
        return s.upvotes, s.downvotes


async def test_set_feedback_set_switch_and_unvote(db_sessionmaker):
    session = await SessionService(db_sessionmaker).create()
    async with db_sessionmaker() as db:
        message = await MessageService(db).create(session.id, "agent", "hi", False)

    async with db_sessionmaker() as db:
        m = await MessageService(db).set_feedback(session.id, message.id, "like")
    assert m.feedback == "like"
    assert await _counters(db_sessionmaker, session.id) == (1, 0)

    # switch like -> dislike moves the count across, no double-count
    async with db_sessionmaker() as db:
        await MessageService(db).set_feedback(session.id, message.id, "dislike")
    assert await _counters(db_sessionmaker, session.id) == (0, 1)

    # unvote clears both the message and the counter
    async with db_sessionmaker() as db:
        m = await MessageService(db).set_feedback(session.id, message.id, None)
    assert m.feedback is None
    assert await _counters(db_sessionmaker, session.id) == (0, 0)


async def test_set_feedback_idempotent_repeat(db_sessionmaker):
    session = await SessionService(db_sessionmaker).create()
    async with db_sessionmaker() as db:
        message = await MessageService(db).create(session.id, "agent", "hi", False)
    async with db_sessionmaker() as db:
        await MessageService(db).set_feedback(session.id, message.id, "like")
    async with db_sessionmaker() as db:
        await MessageService(db).set_feedback(session.id, message.id, "like")
    assert await _counters(db_sessionmaker, session.id) == (1, 0)


async def test_set_feedback_rejects_other_session(db_sessionmaker):
    sessions = SessionService(db_sessionmaker)
    a = await sessions.create()
    b = await sessions.create()
    async with db_sessionmaker() as db:
        message = await MessageService(db).create(a.id, "agent", "hi", False)
    with pytest.raises(NotFoundError):
        async with db_sessionmaker() as db:
            await MessageService(db).set_feedback(b.id, message.id, "like")
    # the wrong-session attempt must not have moved a's counters
    assert await _counters(db_sessionmaker, a.id) == (0, 0)
