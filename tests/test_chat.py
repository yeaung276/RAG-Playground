import json

import pytest_asyncio

from app.models.session import Session


@pytest_asyncio.fixture
async def active_session_id(db_sessionmaker):
    async with db_sessionmaker() as db:
        session = Session(id="sess-active", status="active")
        db.add(session)
        await db.commit()
    return session.id


async def test_send_without_cookie_is_unauthorized(client):
    resp = await client.post("/api/messages", json={"sender": "user", "content": "hi"})
    assert resp.status_code == 401


async def test_send_with_unknown_cookie_is_unauthorized(client):
    resp = await client.post(
        "/api/messages",
        json={"sender": "user", "content": "hi"},
        headers={"Cookie": "chat_session=does-not-exist"},
    )
    assert resp.status_code == 401


async def test_send_with_active_session_cookie_streams_the_reply(
    client, active_session_id
):
    resp = await client.post(
        "/api/messages",
        json={"sender": "user", "content": "hi"},
        headers={"Cookie": f"chat_session={active_session_id}"},
    )
    assert resp.status_code == 200
    frames = [
        json.loads(line[5:])
        for line in resp.text.splitlines()
        if line.startswith("data:")
    ]
    assert frames[0] == {"type": "token", "delta": "echo:hi"}
    assert frames[-1]["type"] == "done"
    assert frames[-1]["id"]


async def test_send_persists_user_and_agent_messages(client, active_session_id):
    await client.post(
        "/api/messages",
        json={"sender": "user", "content": "hi"},
        headers={"Cookie": f"chat_session={active_session_id}"},
    )
    resp = await client.get(
        "/api/messages", headers={"Cookie": f"chat_session={active_session_id}"}
    )
    assert resp.status_code == 200
    rows = resp.json()
    # Order-insensitive: user + agent messages land in the same SQLite second, so
    # created_at ties (chronological order is covered by test_message_service).
    assert sorted((r["sender"], r["content"]) for r in rows) == sorted(
        [("user", "hi"), ("agent", "echo:hi")]
    )
