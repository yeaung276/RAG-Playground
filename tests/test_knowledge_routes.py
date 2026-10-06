"""End-to-end route tests: real app, real DB layer (in-memory SQLite),
mocked blob storage. Exercises the HTTP surface, not the services directly."""

import pytest
import pytest_asyncio
from qdrant_client import models

import app.services.models.model_service as model_service_module
from app.models.model import Model

DIM = 4

DEFAULT_CONFIG = {
    "chunkingMethod": "recursive",
    "chunkingModelId": None,
    "maxChunkSize": 1024,
    "minChunkSize": 256,
    "indexTypes": [{"type": "bm25"}],
    "reranker": None,
    "queryExpansion": None,
}


class FakeTEIEmbedder:
    """Stands in for the TEI client ModelService builds for a registered model."""

    def __init__(self, model: str, *_args, **_kwargs):
        self.model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] + [0.0] * (DIM - 1) for _ in texts]


@pytest.fixture(autouse=True)
def fake_tei(monkeypatch):
    monkeypatch.setattr(model_service_module, "TEIEmbedder", FakeTEIEmbedder)


@pytest_asyncio.fixture
async def embed_id(db_sessionmaker) -> str:
    """A registered TEI bi-encoder, as the model picker would offer it."""
    async with db_sessionmaker() as session:
        row = Model(provider="local", schema="tei", base_url="http://tei",
                    name="embed", capability="bi-encoder")
        session.add(row)
        await session.commit()
        return row.id


def _fe_config(embed_id: str, **overrides) -> dict:
    """What NewKbModal submits for a hybrid, semantic, reranked base."""
    return {
        "chunkingMethod": "semantic",
        "chunkingModelId": embed_id,
        "maxChunkSize": 2000,
        "minChunkSize": 400,
        "indexTypes": [{"type": "bm25"}, {"type": "vector", "modelId": embed_id}],
        "reranker": {"type": "cross-encoder", "modelId": "rerank-1"},
        "queryExpansion": {"modelId": "chat-1"},
        **overrides,
    }


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
    assert kb["config"] == DEFAULT_CONFIG


async def test_create_with_the_frontend_payload_round_trips(client, embed_id, qdrant):
    config = _fe_config(embed_id)
    r = await client.post("/api/admin/knowledge", json={"name": "Tuned", "config": config})
    assert r.status_code == 201
    kb = r.json()
    assert kb["config"] == config
    assert (await client.get(f"/api/admin/knowledge/{kb['id']}")).json()["config"] == config

    params = (await qdrant.get_collection(kb["id"])).config.params
    assert {name: v.size for name, v in params.vectors.items()} == {embed_id: DIM}
    assert list(params.sparse_vectors) == ["bm25"]


async def test_create_with_an_unregistered_embedding_model_returns_404(client):
    r = await client.post(
        "/api/admin/knowledge",
        json={"name": "Bad", "config": {"indexTypes": [{"type": "vector", "modelId": "gone"}]}},
    )
    assert r.status_code == 404
    assert (await client.get("/api/admin/knowledge")).json() == []


@pytest.mark.parametrize(
    "config",
    [
        {"maxChunkSize": 256, "minChunkSize": 256},
        {"indexTypes": []},
        {"indexTypes": [{"type": "totally-made-up"}]},
        {"indexTypes": ["bm25"]},
        {"indexTypes": [{"type": "vector"}]},
        {"chunkingMethod": "semantic", "chunkingModelId": None},
        {"reranker": {"type": "cross-encoder"}},
        {"queryExpansion": {"modelId": ""}},
    ],
    ids=["child-not-smaller", "no-index", "unknown-index", "legacy-index-string",
         "vector-without-model", "semantic-without-model", "reranker-without-model",
         "query-expansion-without-model"],
)
async def test_create_rejects_invalid_config(client, config):
    r = await client.post("/api/admin/knowledge", json={"name": "Bad", "config": config})
    assert r.status_code == 422


async def test_uploaded_file_inherits_kb_config(client, embed_id):
    config = _fe_config(embed_id)
    kb = (
        await client.post("/api/admin/knowledge", json={"name": "Tuned", "config": config})
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
    assert detail["config"] == config


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


async def _upload(client, kb_id: str, name: str) -> dict:
    return (
        await client.post(
            f"/api/admin/knowledge/{kb_id}/files",
            files={"files": (name, b"x", "application/pdf")},
        )
    ).json()[0]


async def _seed_points(qdrant, kb_id: str, *node_ids: str) -> None:
    """Stand in for indexing: one bm25 point per node."""
    await qdrant.upsert(
        kb_id,
        points=[
            models.PointStruct(
                id=i,
                vector={"bm25": models.SparseVector(indices=[i], values=[1.0])},
                payload={"chunk_id": f"p{i}", "node_id": node_id},
            )
            for i, node_id in enumerate(node_ids)
        ],
    )


async def _point_node_ids(qdrant, kb_id: str) -> list[str]:
    points = (await qdrant.scroll(kb_id, limit=100))[0]
    return sorted(p.payload["node_id"] for p in points)


async def test_delete_file_drops_only_its_vectors(client, storage, qdrant):
    kb = await _create_base(client)
    gone, kept = await _upload(client, kb["id"], "a.pdf"), await _upload(client, kb["id"], "b.pdf")
    await _seed_points(qdrant, kb["id"], gone["id"], kept["id"])

    r = await client.delete(f"/api/admin/knowledge/{kb['id']}/nodes/{gone['id']}")

    assert r.status_code == 204
    assert await _point_node_ids(qdrant, kb["id"]) == [kept["id"]]
    assert len(storage.blobs) == 1


async def test_delete_file_still_removes_vectors_when_the_blob_is_already_gone(
    client, storage, qdrant
):
    kb = await _create_base(client)
    node = await _upload(client, kb["id"], "a.pdf")
    await _seed_points(qdrant, kb["id"], node["id"])
    storage.blobs.clear()

    r = await client.delete(f"/api/admin/knowledge/{kb['id']}/nodes/{node['id']}")

    assert r.status_code == 204
    assert await _point_node_ids(qdrant, kb["id"]) == []


async def test_vector_cleanup_failure_does_not_fail_the_delete(
    client, storage, qdrant, monkeypatch
):
    """Cleanup runs after the response, best-effort: the row is gone either way."""
    from app.services.retrieval.indexing_service import IndexingService

    async def boom(self, **_kwargs):
        raise RuntimeError("qdrant down")

    monkeypatch.setattr(IndexingService, "delete_index", boom)
    kb = await _create_base(client)
    node = await _upload(client, kb["id"], "a.pdf")

    r = await client.delete(f"/api/admin/knowledge/{kb['id']}/nodes/{node['id']}")

    assert r.status_code == 204
    assert (await client.get(f"/api/admin/knowledge/{kb['id']}/nodes")).json() == []
    # one try covers both steps, so a vector failure also skips the blob
    assert len(storage.blobs) == 1


async def test_delete_empty_folder_touches_no_vectors(client, qdrant):
    kb = await _create_base(client)
    file = await _upload(client, kb["id"], "a.pdf")
    await _seed_points(qdrant, kb["id"], file["id"])
    folder = (
        await client.post(f"/api/admin/knowledge/{kb['id']}/folders", json={"name": "docs"})
    ).json()

    r = await client.delete(f"/api/admin/knowledge/{kb['id']}/nodes/{folder['id']}")

    assert r.status_code == 204
    assert await _point_node_ids(qdrant, kb["id"]) == [file["id"]]


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
