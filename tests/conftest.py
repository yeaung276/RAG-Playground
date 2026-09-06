from io import BytesIO
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from qdrant_client import AsyncQdrantClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.dependencies.services as deps_services
import app.routers.admin.chat as admin_chat_router
import app.routers.chat as chat_router
from app.app import app
from app.db.base import Base
from app.dependencies.admin import require_admin
from app.dependencies.database import get_session
from app.dependencies.services import (
    get_generation_service,
    get_message_service,
    get_session_service,
)
from app.models.admin import Admin
from app.schemas.messages import TokenFrame
from app.services.chat.message_service import MessageService
from app.services.chat.session_service import SessionService


class FakeGeneration:
    agent = "agent"

    async def stream_reply(self, message=None, img_b64=None):
        yield TokenFrame(delta=f"echo:{message}")


class MockStorage:
    """In-memory blob store implementing the Storage protocol."""

    def __init__(self):
        self.blobs: dict[str, bytes] = {}

    async def save(self, data: bytes, path: str) -> None:
        self.blobs[path] = bytes(data)

    async def load(self, path: str) -> BytesIO:
        return BytesIO(self.blobs[path])

    async def delete(self, path: str) -> None:
        self.blobs.pop(path, None)


class FakeOCR:
    """Stand-in for the OCR service so the background processor needs no creds.
    Reports nothing as OCR-able, so `process` cleanly no-ops."""

    def is_supported(self, mime_type: str | None) -> bool:
        return False


@pytest_asyncio.fixture
async def db_sessionmaker():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # The pubsub publish path emits `SELECT pg_notify(...)`, which SQLite has no
    # function for. Register it as a no-op so the write commits; delivery itself
    # is covered by the Postgres LISTEN/NOTIFY path, not these tests.
    @event.listens_for(engine.sync_engine, "connect")
    def _register_pg_notify(dbapi_conn, _record):
        dbapi_conn.create_function("pg_notify", 2, lambda *_: None)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


@pytest_asyncio.fixture
async def storage():
    return MockStorage()


@pytest_asyncio.fixture
async def qdrant():
    """Qdrant's local mode: the real client against an in-process store, so the
    knowledge routes need no server. Payload indexes are a no-op here."""
    client = AsyncQdrantClient(":memory:")
    yield client
    await client.close()


@pytest_asyncio.fixture
async def client(db_sessionmaker, storage, qdrant):
    async def _message_service():
        async with db_sessionmaker() as db:
            yield MessageService(db)

    async def _get_session():
        async with db_sessionmaker() as db:
            yield db

    app.dependency_overrides[get_session_service] = lambda: SessionService(db_sessionmaker)
    app.dependency_overrides[get_generation_service] = lambda: FakeGeneration()
    app.dependency_overrides[get_message_service] = _message_service
    app.dependency_overrides[get_session] = _get_session
    # Admin routes are guarded; satisfy the guard by default. Tests that
    # exercise the guard itself pop this override.
    app.dependency_overrides[require_admin] = lambda: Admin(
        id="admin-test", username="tester"
    )

    # kb/file services and the background processor resolve storage via
    # deps_services.get_storage (not via Depends), so patch it there.
    original_deps_get_storage = deps_services.get_storage
    deps_services.get_storage = lambda: storage

    # The background processor also builds the extraction service (which reads
    # creds from the env); swap in a no-op so tests need no endpoint configured.
    original_deps_get_extraction = deps_services.get_extraction_service
    deps_services.get_extraction_service = lambda: FakeOCR()

    # The kb service and the background processor read the client off this module
    # rather than via Depends, so point it at the local-mode one.
    original_deps_qdrant = deps_services.qdrant
    deps_services.qdrant = qdrant

    # The chat send / admin intercept flows open their own short-lived session
    # via the module-global async_session_maker (not via Depends), so it bypasses
    # the get_session override. Point it at the test engine so those writes land
    # in the same DB the DI'd reads use.
    original_chat_maker = chat_router.async_session_maker
    original_admin_maker = admin_chat_router.async_session_maker
    chat_router.async_session_maker = db_sessionmaker
    admin_chat_router.async_session_maker = db_sessionmaker

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    deps_services.get_storage = original_deps_get_storage
    deps_services.get_extraction_service = original_deps_get_extraction
    deps_services.qdrant = original_deps_qdrant
    chat_router.async_session_maker = original_chat_maker
    admin_chat_router.async_session_maker = original_admin_maker
    app.dependency_overrides.clear()
