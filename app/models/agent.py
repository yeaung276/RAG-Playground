from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, LargeBinary, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.ids import new_id

# JSONB on Postgres (prod + migrations), generic JSON on SQLite (tests).
_JSON = JSON().with_variant(JSONB(), "postgresql")


class Agent(Base):
    """A configured agent. `tools` and `handoff` are whole-document columns
    rewritten on every save; each tool's `authToken` is encrypted with the
    row's `tools_dek` under AAD "<agent id>:<tool name>"."""

    __tablename__ = "agents"

    __table_args__ = (
        UniqueConstraint("name", name="uq_agents_name"),
        Index(
            "uq_agents_entrypoint",
            "is_entrypoint",
            unique=True,
            postgresql_where=text("is_entrypoint"),
            sqlite_where=text("is_entrypoint"),
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(index=True)
    description: Mapped[str] = mapped_column(default="")
    instruction: Mapped[str] = mapped_column(default="")
    model_id: Mapped[str | None] = mapped_column(
        ForeignKey("models.id"), index=True, default=None
    )
    temperature: Mapped[int] = mapped_column(default=0)
    knowledge_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_bases.id"), index=True, default=None
    )
    max_step: Mapped[int] = mapped_column(default=10)
    tools: Mapped[list[dict[str, Any]]] = mapped_column(
        _JSON, nullable=False, default=list, server_default="[]"
    )
    handoff: Mapped[dict[str, Any]] = mapped_column(
        _JSON, nullable=False, default=dict, server_default='{"mode": "none", "targets": []}'
    )
    is_entrypoint: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    tools_dek: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
