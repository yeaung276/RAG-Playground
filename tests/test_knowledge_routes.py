"""End-to-end route tests: real app, real DB layer (in-memory SQLite),
mocked blob storage. Exercises the HTTP surface, not the services directly."""


async def _create_base(client, name="Coins"):
    r = await client.post("/api/admin/knowledge", json={"name": name})
    assert r.status_code == 201
    return r.json()


# --- knowledge bases ---------------------------------------------------------
async def test_create_and_list_bases(client):
    kb = await _create_base(client, "Coins")
    assert kb["name"] == "Coins"
    assert kb["fileCount"] == 0
    assert isinstance(kb["id"], str) and kb["id"]

    r = await client.get("/api/admin/knowledge")
    assert r.status_code == 200
    bases = r.json()
    assert [b["id"] for b in bases] == [kb["id"]]


async def test_get_base(client):
    kb = await _create_base(client)
    r = await client.get(f"/api/admin/knowledge/{kb['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == kb["id"]


async def test_get_missing_base_returns_404(client):
    r = await client.get("/api/admin/knowledge/does-not-exist")
    assert r.status_code == 404
    assert "detail" in r.json()


# --- config ------------------------------------------------------------------
async def test_create_applies_default_config(client):
    kb = await _create_base(client)
    assert kb["config"] == {
        "chunkingMethod": "semantic",
        "maxChunkSize": 1024,
        "minChunkSize": 256,
        "indexTypes": ["bm25"],
    }


async def test_create_with_explicit_config(client):
    r = await client.post(
        "/api/admin/knowledge",
        json={
            "name": "Tuned",
            "config": {
                "maxChunkSize": 2000,
                "minChunkSize": 400,
                "indexTypes": ["text-embedding-3-large"],
            },
        },
    )
    assert r.status_code == 201
    assert r.json()["config"]["maxChunkSize"] == 2000
    assert r.json()["config"]["indexTypes"] == ["text-embedding-3-large"]


async def test_patch_config_marks_completed_files_out_of_sync(client, db_sessionmaker):
    from app.models.node import Node

    kb = await _create_base(client)
    completed = (
        await client.post(
            f"/api/admin/knowledge/{kb['id']}/files",
            files={"files": ("done.pdf", b"x", "application/pdf")},
        )
    ).json()[0]
    failed = (
        await client.post(
            f"/api/admin/knowledge/{kb['id']}/files",
            files={"files": ("bad.pdf", b"y", "application/pdf")},
        )
    ).json()[0]

    # Force known terminal states (background OCR isn't exercised here).
    async with db_sessionmaker() as s:
        (await s.get(Node, completed["id"])).status = "completed" # type: ignore
        (await s.get(Node, failed["id"])).status = "failed" # type: ignore
        await s.commit()

    r = await client.patch(
        f"/api/admin/knowledge/{kb['id']}",
        json={"config": {"maxChunkSize": 1500, "minChunkSize": 300,
                         "indexTypes": ["BAAI/bge-m3"]}},
    )
    assert r.status_code == 200
    assert r.json()["config"]["maxChunkSize"] == 1500

    nodes = {n["id"]: n for n in (
        await client.get(f"/api/admin/knowledge/{kb['id']}/nodes")
    ).json()}
    # completed → out_of_sync; failed left untouched
    assert nodes[completed["id"]]["status"] == "out_of_sync"
    assert nodes[failed["id"]]["status"] == "failed"


async def test_create_rejects_child_not_smaller_than_parent(client):
    r = await client.post(
        "/api/admin/knowledge",
        json={
            "name": "Bad",
            "config": {"maxChunkSize": 256, "minChunkSize": 256,
                       "indexTypes": ["BAAI/bge-m3"]},
        },
    )
    assert r.status_code == 422


async def test_create_rejects_unknown_index_type(client):
    r = await client.post(
        "/api/admin/knowledge",
        json={
            "name": "Bad",
            "config": {"maxChunkSize": 1024, "minChunkSize": 256,
                       "indexTypes": ["totally-made-up"]},
        },
    )
    assert r.status_code == 422


async def test_uploaded_file_inherits_kb_config(client):
    kb = (
        await client.post(
            "/api/admin/knowledge",
            json={
                "name": "Tuned",
                "config": {"maxChunkSize": 2000, "minChunkSize": 400,
                           "indexTypes": ["text-embedding-3-large"]},
            },
        )
    ).json()
    node = (
        await client.post(
            f"/api/admin/knowledge/{kb['id']}/files",
            files={"files": ("a.pdf", b"x", "application/pdf")},
        )
    ).json()[0]

    detail = (
        await client.get(f"/api/admin/knowledge/{kb['id']}/files/{node['id']}")
    ).json()
    assert detail["config"] == {
        "chunkingMethod": "semantic",
        "maxChunkSize": 2000,
        "minChunkSize": 400,
        "indexTypes": ["text-embedding-3-large"],
    }


async def test_patch_missing_base_returns_404(client):
    r = await client.patch(
        "/api/admin/knowledge/nope",
        json={"config": {"maxChunkSize": 1024, "minChunkSize": 256,
                         "indexTypes": ["BAAI/bge-m3"]}},
    )
    assert r.status_code == 404


# --- folders / uploads / tree ------------------------------------------------
async def test_create_folder_and_tree(client):
    kb = await _create_base(client)
    r = await client.post(f"/api/admin/knowledge/{kb['id']}/folders", json={"name": "docs"})
    assert r.status_code == 201
    folder = r.json()
    assert folder["type"] == "folder"
    assert folder["parentId"] is None

    root = (await client.get(f"/api/admin/knowledge/{kb['id']}/nodes")).json()
    assert [n["id"] for n in root] == [folder["id"]]


async def test_upload_file_stores_blob_and_nests_in_tree(client, storage):
    kb = await _create_base(client)
    folder = (
        await client.post(f"/api/admin/knowledge/{kb['id']}/folders", json={"name": "docs"})
    ).json()

    r = await client.post(
        f"/api/admin/knowledge/{kb['id']}/files?parent={folder['id']}",
        files={"files": ("a.pdf", b"hello pdf", "application/pdf")},
    )
    assert r.status_code == 201
    node = r.json()[0]
    assert node["type"] == "file"
    assert node["size"] == len(b"hello pdf")
    assert node["mimeType"] == "application/pdf"
    assert node["parentId"] == folder["id"]

    # blob landed in (mock) storage, keyed under the KB
    assert len(storage.blobs) == 1
    key = next(iter(storage.blobs))
    assert key.startswith(f"{kb['id']}/")
    assert storage.blobs[key] == b"hello pdf"

    # file is listed under its parent folder
    children = (
        await client.get(f"/api/admin/knowledge/{kb['id']}/nodes?parent={folder['id']}")
    ).json()
    assert [n["id"] for n in children] == [node["id"]]

    # file_count on the base updates
    base = (await client.get(f"/api/admin/knowledge/{kb['id']}")).json()
    assert base["fileCount"] == 1


async def test_list_nodes_by_parent(client):
    kb = await _create_base(client)
    folder = (
        await client.post(f"/api/admin/knowledge/{kb['id']}/folders", json={"name": "docs"})
    ).json()
    await client.post(
        f"/api/admin/knowledge/{kb['id']}/files?parent={folder['id']}",
        files={"files": ("a.pdf", b"x", "application/pdf")},
    )

    root = (await client.get(f"/api/admin/knowledge/{kb['id']}/nodes")).json()
    assert [n["name"] for n in root] == ["docs"]

    children = (
        await client.get(f"/api/admin/knowledge/{kb['id']}/nodes?parent={folder['id']}")
    ).json()
    assert [n["name"] for n in children] == ["a.pdf"]


# --- download ----------------------------------------------------------------
async def test_download_returns_bytes(client):
    kb = await _create_base(client)
    node = (
        await client.post(
            f"/api/admin/knowledge/{kb['id']}/files",
            files={"files": ("a.pdf", b"hello pdf", "application/pdf")},
        )
    ).json()[0]

    r = await client.get(f"/api/admin/knowledge/{kb['id']}/files/{node['id']}/download")
    assert r.status_code == 200
    assert r.content == b"hello pdf"
    assert r.headers["content-type"].startswith("application/pdf")
    assert "attachment" in r.headers["content-disposition"]


async def test_download_missing_file_returns_404(client):
    kb = await _create_base(client)
    r = await client.get(f"/api/admin/knowledge/{kb['id']}/files/nope/download")
    assert r.status_code == 404


# --- resync ------------------------------------------------------------------
async def test_resync_updates_timestamp(client):
    kb = await _create_base(client)
    node = (
        await client.post(
            f"/api/admin/knowledge/{kb['id']}/files",
            files={"files": ("a.pdf", b"x", "application/pdf")},
        )
    ).json()[0]

    r = await client.post(f"/api/admin/knowledge/{kb['id']}/files/{node['id']}/resync")
    assert r.status_code == 200
    assert r.json()["id"] == node["id"]


# --- delete ------------------------------------------------------------------
async def test_delete_file_cleans_blob(client, storage):
    kb = await _create_base(client)
    node = (
        await client.post(
            f"/api/admin/knowledge/{kb['id']}/files",
            files={"files": ("a.pdf", b"hello", "application/pdf")},
        )
    ).json()[0]
    assert len(storage.blobs) == 1

    r = await client.delete(f"/api/admin/knowledge/{kb['id']}/nodes/{node['id']}")
    assert r.status_code == 204
    assert storage.blobs == {}


async def test_delete_nonempty_folder_conflicts(client):
    kb = await _create_base(client)
    folder = (
        await client.post(f"/api/admin/knowledge/{kb['id']}/folders", json={"name": "docs"})
    ).json()
    child = (
        await client.post(
            f"/api/admin/knowledge/{kb['id']}/files?parent={folder['id']}",
            files={"files": ("a.pdf", b"x", "application/pdf")},
        )
    ).json()[0]

    r = await client.delete(f"/api/admin/knowledge/{kb['id']}/nodes/{folder['id']}")
    assert r.status_code == 409

    # once emptied, the folder deletes
    assert (
        await client.delete(f"/api/admin/knowledge/{kb['id']}/nodes/{child['id']}")
    ).status_code == 204
    assert (
        await client.delete(f"/api/admin/knowledge/{kb['id']}/nodes/{folder['id']}")
    ).status_code == 204


async def test_delete_missing_node_returns_404(client):
    kb = await _create_base(client)
    r = await client.delete(f"/api/admin/knowledge/{kb['id']}/nodes/nope")
    assert r.status_code == 404
