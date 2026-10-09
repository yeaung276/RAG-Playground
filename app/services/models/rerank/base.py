from typing import Protocol

from app.logger import get_logger

logger = get_logger("services.rerank")


class Reranker(Protocol):
    """Scores query-passage pairs. One instance is bound to one model. `chunk_ids`
    identify each text, for rerankers that score stored vectors instead of text.
    Scores come back in input order; ordering is the caller's job."""

    model: str

    async def rank(
        self, query: str, texts: list[str], chunk_ids: list[str]
    ) -> list[float]: ...
