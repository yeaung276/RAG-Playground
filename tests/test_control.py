from sqlalchemy import func, select

from app.models.session import Session
from app.routers.control import control
from app.services.chat.session_service import SessionService


def _cookie_header(response):
    for name, value in response.raw_headers:
        if name == b"set-cookie" and value.startswith(b"chat_session="):
            return value.decode()
    return None


def _cookie_session_id(response):
    return _cookie_header(response).split("chat_session=")[1].split(";")[0]


async def _session_row(db_sessionmaker, session_id):
    async with db_sessionmaker() as db:
        return (
            await db.execute(select(Session).where(Session.id == session_id))
        ).scalar_one()


async def _drive(endpoint, db_sessionmaker):
    response = await endpoint(
        new=False, session_id=None, sessions=SessionService(db_sessionmaker)
    )

    session_id = _cookie_session_id(response)
    assert "httponly" in _cookie_header(response).lower()

    gen = response.body_iterator
    first = await gen.__anext__()
    assert first == ": connected\n\n"

    # session is active while the stream is held open
    opened = await _session_row(db_sessionmaker, session_id)
    assert opened.status == "active"

    # ending the stream marks the session disconnected (not closed) so it can reattach
    await gen.aclose()
    dropped = await _session_row(db_sessionmaker, session_id)
    assert dropped.status == "disconnected"
    assert dropped.disconnected_at is not None


async def test_control_opens_and_disconnects_session(db_sessionmaker):
    await _drive(control, db_sessionmaker)


async def test_control_reattaches_disconnected_session(db_sessionmaker):
    async with db_sessionmaker() as db:
        db.add(
            Session(
                id="sess-x",
                status="disconnected",
                disconnected_at=func.now(),
            )
        )
        await db.commit()

    response = await control(
        new=False, session_id="sess-x", sessions=SessionService(db_sessionmaker)
    )
    assert _cookie_session_id(response) == "sess-x"

    gen = response.body_iterator
    await gen.__anext__()
    row = await _session_row(db_sessionmaker, "sess-x")
    assert row.status == "active"
    await gen.aclose()


async def test_control_new_forces_fresh_session(db_sessionmaker):
    async with db_sessionmaker() as db:
        db.add(Session(id="sess-x", status="active"))
        await db.commit()

    response = await control(
        new=True, session_id="sess-x", sessions=SessionService(db_sessionmaker)
    )
    assert _cookie_session_id(response) != "sess-x"

    gen = response.body_iterator
    await gen.__anext__()
    await gen.aclose()
