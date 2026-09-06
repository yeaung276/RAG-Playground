from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.ids import new_id


class Chunk(Base):
    """A unit of extracted content for a document (file node). OCR produces one
    chunk per PDF page or one per image; chunks are keyed to their source node."""

    __tablename__ = "knowledge_chunks"

    __table_args__ = (
        Index("ix_knowledge_chunks_node_id_seq", "node_id", "seq"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    node_id: Mapped[str] = mapped_column(ForeignKey("knowledge_nodes.id"))
    kb_id: Mapped[str] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    seq: Mapped[int]  # 0-based order within the document
    content: Mapped[str]
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
