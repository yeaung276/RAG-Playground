"""End-to-end route tests for GET /api/admin/chats: real app + in-memory DB."""
from datetime import datetime, timezone

from app.app import app
from app.config import get_settings
from app.dependencies.admin import require_admin
from app.models.session import Session
from app.services.admin.admin_service import AdminService
from app.utils.token import sign_token


def _dt(day: int) -> datetime:
    return datetime(2026, 1, day, 12, 0, tzinfo=timezone.utc)


async def _seed(db_sessionmaker, rows: list[dict]):
    async with db_sessionmaker() as db:
        for r in rows:
            db.add(Session(**r))
        await db.commit()


# --- auth guard --------------------------------------------------------------
async def test_requires_admin_session(client):
    app.dependency_overrides.pop(require_admin, None)
    r = await client.get("/api/admin/chats/current")
    assert r.status_code == 401


async def test_valid_admin_cookie_authorizes(client, db_sessionmaker):
    app.dependency_overrides.pop(require_admin, None)
    async with db_sessionmaker() as db:
        admin = await AdminService(db).create("boss", "pw")
    token = sign_token(admin.id, get_settings().ADMIN_SECRET_KEY)

    r = await client.get(
        "/api/admin/chats/current",
        headers={"Cookie": f"{get_settings().ADMIN_COOKIE_NAME}={token}"},
    )
    assert r.status_code == 200


# --- current view ------------------------------------------------------------
async def test_current_returns_only_live(client, db_sessionmaker):
    await _seed(
        db_sessionmaker,
        [
            {"id": "a", "status": "active"},
            {"id": "b", "status": "disconnected"},
            {"id": "c", "status": "active"},
            {"id": "d", "status": "active", "intercepted": True},
        ],
    )
    r = await client.get("/api/admin/chats/current")
    assert r.status_code == 200
    body = r.json()
    # active AND not currently intercepted (d is being handled -> excluded)
    assert body["total"] == 2
    assert {i["id"] for i in body["items"]} == {"a", "c"}
    assert all(i["status"] == "active" for i in body["items"])


async def test_current_applies_date_filter(client, db_sessionmaker):
    await _seed(
        db_sessionmaker,
        [{"id": "a", "status": "active", "created_at": _dt(1)}],
    )
    r = await client.get(
        "/api/admin/chats/current", params={"from": _dt(10).isoformat()}
    )
    assert r.json()["total"] == 0


# --- history view ------------------------------------------------------------
async def test_history_returns_all_newest_first(client, db_sessionmaker):
    await _seed(
        db_sessionmaker,
        [
            {"id": "old", "status": "active", "created_at": _dt(1)},
            {"id": "mid", "status": "disconnected", "created_at": _dt(2)},
            {"id": "new", "status": "active", "created_at": _dt(3)},
        ],
    )
    r = await client.get("/api/admin/chats/history")
    body = r.json()
    assert body["total"] == 3
    assert [i["id"] for i in body["items"]] == ["new", "mid", "old"]


async def test_history_date_range_filter(client, db_sessionmaker):
    await _seed(
        db_sessionmaker,
        [
            {"id": "d1", "status": "active", "created_at": _dt(1)},
            {"id": "d2", "status": "active", "created_at": _dt(2)},
            {"id": "d3", "status": "active", "created_at": _dt(3)},
        ],
    )
    r = await client.get(
        "/api/admin/chats/history",
        params={"from": _dt(2).isoformat(), "to": _dt(2).isoformat()},
    )
    body = r.json()
    assert [i["id"] for i in body["items"]] == ["d2"]
    assert body["total"] == 1


async def test_pagination(client, db_sessionmaker):
    await _seed(
        db_sessionmaker,
        [
            {"id": f"s{n}", "status": "active", "created_at": _dt(n)}
            for n in range(1, 6)
        ],
    )
    r1 = await client.get(
        "/api/admin/chats/history", params={"page": 1, "pageSize": 2}
    )
    r3 = await client.get(
        "/api/admin/chats/history", params={"page": 3, "pageSize": 2}
    )
    assert r1.json()["total"] == 5
    assert len(r1.json()["items"]) == 2
    assert [i["id"] for i in r1.json()["items"]] == ["s5", "s4"]
    assert [i["id"] for i in r3.json()["items"]] == ["s1"]


async def test_response_shape_has_calculated_fields(client, db_sessionmaker):
    await _seed(
        db_sessionmaker,
        [{"id": "a", "status": "active", "created_at": _dt(1)}],
    )
    item = (await client.get("/api/admin/chats/history")).json()["items"][0]
    assert item == {
        "id": "a",
        "status": "active",
        "createdAt": item["createdAt"],
        "triggerMessage": None,
        "priority": 0,
        "upvotes": 0,
        "downvotes": 0,
    }
