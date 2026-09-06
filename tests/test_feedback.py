"""End-to-end feedback loop: widget POST -> message.feedback + session counters
-> echoed on fetch and rolled up in the admin list."""
from app.config import get_settings
from app.models.message import Message
from app.models.session import Session


async def _seed_session_with_message(db_sessionmaker):
    async with db_sessionmaker() as db:
        db.add(Session(id="sess-fb", status="active"))
        db.add(Message(id="msg-1", session_id="sess-fb", sender="agent", content="hi"))
        await db.commit()


def _cookie(session_id: str) -> dict[str, str]:
    return {"Cookie": f"{get_settings().SESSION_COOKIE_NAME}={session_id}"}


async def _list_votes(client) -> tuple[int, int]:
    item = (await client.get("/api/admin/chats/history")).json()["items"][0]
    return item["upvotes"], item["downvotes"]


async def test_feedback_requires_session(client):
    r = await client.post("/api/messages/msg-1/feedback", json={"value": "like"})
    assert r.status_code == 401


async def test_feedback_rejects_message_in_other_session(client, db_sessionmaker):
    await _seed_session_with_message(db_sessionmaker)
    async with db_sessionmaker() as db:
        db.add(Session(id="sess-other", status="active"))
        await db.commit()
    r = await client.post(
        "/api/messages/msg-1/feedback", json={"value": "like"}, headers=_cookie("sess-other")
    )
    assert r.status_code == 404


async def test_feedback_set_echoes_and_rolls_up(client, db_sessionmaker):
    await _seed_session_with_message(db_sessionmaker)

    r = await client.post(
        "/api/messages/msg-1/feedback", json={"value": "like"}, headers=_cookie("sess-fb")
    )
    assert r.status_code == 200
    assert r.json()["feedback"] == "like"

    # re-display: the vote comes back on the transcript fetch
    rows = (await client.get("/api/messages", headers=_cookie("sess-fb"))).json()
    assert rows[0]["feedback"] == "like"

    # admin list rolls it up
    assert await _list_votes(client) == (1, 0)


async def test_feedback_switch_and_unvote_rolls_up(client, db_sessionmaker):
    await _seed_session_with_message(db_sessionmaker)

    await client.post(
        "/api/messages/msg-1/feedback", json={"value": "like"}, headers=_cookie("sess-fb")
    )
    await client.post(
        "/api/messages/msg-1/feedback", json={"value": "dislike"}, headers=_cookie("sess-fb")
    )
    assert await _list_votes(client) == (0, 1)

    r = await client.post(
        "/api/messages/msg-1/feedback", json={"value": None}, headers=_cookie("sess-fb")
    )
    assert r.json()["feedback"] is None
    assert await _list_votes(client) == (0, 0)
