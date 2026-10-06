from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import CamelModel
from app.services.retrieval.document import KbConfig


# ── Knowledge bases ─────────────────────────────────────────────────────────


class KnowledgeBaseCreate(CamelModel):
    name: str
    config: KbConfig = Field(default_factory=KbConfig)


class KnowledgeBaseRead(CamelModel):
    id: str
    name: str
    description: str | None
    config: KbConfig
    file_count: int
    created_at: datetime


class KnowledgeBaseUpdate(CamelModel):
    config: KbConfig


# ── Nodes & files ───────────────────────────────────────────────────────────

NodeStatus = Literal["processing", "completed", "failed", "out_of_sync"]


class FolderCreate(CamelModel):
    parent_id: str | None = None
    name: str


class NodeRead(CamelModel):
    id: str
    kb_id: str
    parent_id: str | None
    name: str
    type: Literal["file", "folder"]
    size: int | None
    mime_type: str | None
    status: NodeStatus | None = None
    error: str | None = None
    updated_at: datetime


class ChunkRead(CamelModel):
    id: str
    seq: int
    content: str


class FileDetail(NodeRead):
    config: KbConfig | None = None
    chunks: list[ChunkRead] = []
