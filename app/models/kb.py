from datetime import datetime
from typing import Any

from sqlalchemy import JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.ids import new_id


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(index=True)
    description: Mapped[str | None] = mapped_column(default=None)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
