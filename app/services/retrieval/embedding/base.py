from typing import Protocol

from qdrant_client import models

from app.logger import get_logger

logger = get_logger("services.embedding")


class Embedder(Protocol):
    """Turns text into vectors, dense or sparse. One instance is bound to one model."""

    model: str

    async def embed(
        self, texts: list[str]
    ) -> list[list[float]] | list[models.SparseVector]: ...
