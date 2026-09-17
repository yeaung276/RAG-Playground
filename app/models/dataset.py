from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.ids import new_id

# JSONB on Postgres (prod + migrations), generic JSON on SQLite (tests).
_JSON = JSON().with_variant(JSONB(), "postgresql")


class Dataset(Base):
    """A generation request and its outcome. The pairs themselves are not rows:
    they live in blob storage as one JSON file at `result_key`, written by the
    background job once generation finishes. `parsed_count` of `file_count`
    is how far that job has got."""

    __tablename__ = "datasets"

    __table_args__ = (UniqueConstraint("name", name="uq_datasets_name"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(index=True)
    source_key: Mapped[str | None] = mapped_column(default=None)
    result_key: Mapped[str | None] = mapped_column(default=None)
    model_id: Mapped[str | None] = mapped_column(
        ForeignKey("models.id", ondelete="SET NULL"), index=True, default=None
    )
    sample_per_file: Mapped[int] = mapped_column(default=3)
    mix: Mapped[dict[str, Any]] = mapped_column(_JSON, nullable=False, default=dict)
    labels: Mapped[list[str]] = mapped_column(
        _JSON, nullable=False, default=list, server_default="[]"
    )
    status: Mapped[str] = mapped_column(index=True, default="pending")
    error: Mapped[str | None] = mapped_column(default=None)
    file_count: Mapped[int] = mapped_column(default=0)
    parsed_count: Mapped[int] = mapped_column(default=0)
    pair_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
