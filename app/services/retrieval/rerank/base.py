from typing import Protocol

from app.logger import get_logger

logger = get_logger("services.rerank")


class Reranker(Protocol):
    """Scores query-passage pairs with a cross-encoder. One instance is bound to
    one model. Scores come back in input order; ordering is the caller's job."""

    model: str

    async def rank(self, query: str, texts: list[str]) -> list[float]: ...
