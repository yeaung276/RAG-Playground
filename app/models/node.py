from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.ids import new_id


class Node(Base):
    """A node in a knowledge base's file tree. The hierarchy lives here (DB);
    file bytes live in blob storage, addressed by `storage_key`."""

    __tablename__ = "knowledge_nodes"
    
    __table_args__ = (
        UniqueConstraint("kb_id", "parent_id", "name", name="uq_node_name"),
        Index("ix_knowledge_nodes_type", "type"),
        Index("ix_knowledge_nodes_status", "status"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    kb_id: Mapped[str] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_nodes.id"), index=True, default=None
    )
    name: Mapped[str]
    type: Mapped[str]  # "file" | "folder"
    size: Mapped[int | None] = mapped_column(default=None)
    mime_type: Mapped[str | None] = mapped_column(default=None)
    storage_key: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str | None] = mapped_column(default=None)
    error: Mapped[str | None] = mapped_column(default=None)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    content: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, default=None
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
