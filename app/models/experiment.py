from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.ids import new_id

_JSON = JSON().with_variant(JSONB(), "postgresql")


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    name: Mapped[str]
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    knowledge_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"), index=True, default=None
    )
    snapshot_retrieval_config: Mapped[dict[str, Any]] = mapped_column(
        _JSON, nullable=False, default=dict
    )
    snapshot_kb_config: Mapped[dict[str, Any] | None] = mapped_column(
        _JSON, default=None
    )
    metrics: Mapped[list[str]] = mapped_column(
        _JSON, nullable=False, default=list, server_default="[]"
    )
    scores: Mapped[dict[str, float] | None] = mapped_column(_JSON, default=None)
    result_path: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(index=True, default="pending")
    error: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
