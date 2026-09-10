import base64

import pytest

from app.config import get_settings

BASE = "/api/admin/agents"


@pytest.fixture(autouse=True)
def kek(monkeypatch):
    monkeypatch.setenv("MODEL_KEK", base64.b64encode(b"k" * 32).decode())
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def test_create_returns_201_with_camel_case_body(client):
    response = await client.post(
        BASE,
        json={
            "name": "router",
            "instruction": "route the user",
            "temperature": 30,
            "maxStep": 5,
            "tools": [{"name": "search", "auth": "bearer", "authToken": "tok-1"}],
            "handoff": {"mode": "manual", "targets": [{"agentId": "a2"}]},
        },
    )
    body = response.json()
    assert response.status_code == 201
    assert (body["maxStep"], body["isEntrypoint"]) == (5, False)
    assert body["tools"][0]["hasAuthToken"] is True
    assert "authToken" not in body["tools"][0]
    assert body["handoff"]["targets"][0]["agentId"] == "a2"


async def test_duplicate_name_returns_409(client):
    await client.post(BASE, json={"name": "router"})
    assert (await client.post(BASE, json={"name": "router"})).status_code == 409


async def test_list_is_unpaginated(client):
    await client.post(BASE, json={"name": "a"})
    await client.post(BASE, json={"name": "b"})
    response = await client.get(BASE)
    assert response.status_code == 200
    assert [a["name"] for a in response.json()] == ["a", "b"]


async def test_list_returns_counts_not_documents(client):
    await client.post(
        BASE,
        json={
            "name": "router",
            "tools": [
                {"name": "search", "enabled": True},
                {"name": "ping", "enabled": False},
            ],
            "handoff": {"mode": "manual", "targets": [{"agentId": "a2"}]},
        },
    )
    row = (await client.get(BASE)).json()[0]
    assert (row["enabledToolCount"], row["handoffCount"], row["handoffMode"]) == (1, 1, "manual")
    assert "tools" not in row and "handoff" not in row


async def test_patch_keeps_the_stored_token(client):
    agent = (
        await client.post(
            BASE,
            json={
                "name": "router",
                "tools": [{"name": "search", "auth": "bearer", "authToken": "tok-1"}],
            },
        )
    ).json()
    response = await client.patch(
        f"{BASE}/{agent['id']}",
        json={"tools": [{"name": "search", "auth": "bearer", "url": "https://example.com"}]},
    )
    tool = response.json()["tools"][0]
    assert (tool["url"], tool["hasAuthToken"]) == ("https://example.com", True)


async def test_set_entrypoint_moves_the_flag(client):
    first = (await client.post(BASE, json={"name": "a"})).json()
    second = (await client.post(BASE, json={"name": "b"})).json()

    await client.put(f"{BASE}/{first['id']}/entrypoint")
    assert (await client.put(f"{BASE}/{second['id']}/entrypoint")).json()["isEntrypoint"] is True
    assert [a["isEntrypoint"] for a in (await client.get(BASE)).json()] == [False, True]


async def test_get_and_delete(client):
    agent = (await client.post(BASE, json={"name": "router"})).json()
    assert (await client.get(f"{BASE}/{agent['id']}")).json()["name"] == "router"
    assert (await client.delete(f"{BASE}/{agent['id']}")).status_code == 204
    assert (await client.get(f"{BASE}/{agent['id']}")).status_code == 404


async def test_name_cannot_be_patched(client):
    agent = (await client.post(BASE, json={"name": "router"})).json()
    body = (await client.patch(f"{BASE}/{agent['id']}", json={"name": "renamed"})).json()
    assert body["name"] == "router"


async def test_temperature_out_of_range_returns_422(client):
    response = await client.post(BASE, json={"name": "router", "temperature": 101})
    assert response.status_code == 422
