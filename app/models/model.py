from datetime import datetime

from sqlalchemy import LargeBinary, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.ids import new_id


class Model(Base):
    """A user-registered model endpoint. `api_key_ct` is the API key encrypted
    with a per-row DEK; `api_key_dek` is that DEK encrypted with the KEK mounted
    from the environment."""

    __tablename__ = "models"

    __table_args__ = (
        UniqueConstraint("provider", "name", "capability", name="uq_models_provider_name_capability"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(index=True)
    schema: Mapped[str]
    base_url: Mapped[str]
    name: Mapped[str]
    capability: Mapped[str] = mapped_column(index=True)
    api_key_ct: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    api_key_dek: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
