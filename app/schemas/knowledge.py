from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import CamelModel
from app.services.retrieval.document import IndexingConfig


# ── Knowledge bases ─────────────────────────────────────────────────────────


class KnowledgeBaseCreate(CamelModel):
    name: str
    config: IndexingConfig = Field(default_factory=IndexingConfig)


class KnowledgeBaseRead(CamelModel):
    id: str
    name: str
    description: str | None
    config: IndexingConfig
    file_count: int
    created_at: datetime


class KnowledgeBaseUpdate(CamelModel):
    config: IndexingConfig


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
    config: IndexingConfig | None = None
    chunks: list[ChunkRead] = []
