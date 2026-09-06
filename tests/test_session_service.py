from app.services.chat.session_service import SessionService


async def test_create_is_active(db_sessionmaker):
    session = await SessionService(db_sessionmaker).create()
    assert session.status == "active"


async def test_get_active_returns_active_session(db_sessionmaker):
    sessions = SessionService(db_sessionmaker)
    created = await sessions.create()
    assert (await sessions.get_active(created.id)) is not None


async def test_disconnect_keeps_session_reattachable(db_sessionmaker):
    sessions = SessionService(db_sessionmaker)
    created = await sessions.create()
    await sessions.disconnect(created.id)
    # still valid (within timeout) even though disconnected
    session = await sessions.get_active(created.id)
    assert session is not None
    assert session.status == "disconnected"


async def test_reconnect_reactivates(db_sessionmaker):
    sessions = SessionService(db_sessionmaker)
    created = await sessions.create()
    await sessions.disconnect(created.id)
    reattached = await sessions.reconnect(created.id)
    assert reattached is not None
    refreshed = await sessions.get_active(created.id)
    assert refreshed.status == "active"
    assert refreshed.disconnected_at is None


async def test_get_or_create_creates_once(db_sessionmaker):
    sessions = SessionService(db_sessionmaker)
    first = await sessions.get_or_create("U123")
    second = await sessions.get_or_create("U123")
    assert first.id == "U123" == second.id
