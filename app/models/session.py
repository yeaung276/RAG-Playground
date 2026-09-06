from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

# JSONB on Postgres (prod + migrations), generic JSON on SQLite (tests).
_JSON_FLAGS = JSON().with_variant(JSONB(), "postgresql")

from app.db.base import Base
from app.db.ids import new_id


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        # Admin "history" list orders/filters by created_at.
        Index("ix_sessions_created_at", "created_at"),
        
        # Admin "current" attention feed: only active, un-intercepted sessions,
        Index(
            "ix_sessions_attention",
            "priority",
            "created_at",
            postgresql_where=text("status = 'active' AND intercepted = false"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", index=True
    )
    status_flags: Mapped[dict[str, Any]] = mapped_column(
        _JSON_FLAGS, nullable=False, default=dict, server_default="{}"
    )
    trigger_message: Mapped[str | None] = mapped_column(String, nullable=True)
    upvotes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    downvotes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    disconnected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    intercepted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    last_intercepted_by: Mapped[str | None] = mapped_column(String, nullable=True)
    last_intercepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
