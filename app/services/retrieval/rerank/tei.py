import asyncio
import os

import httpx
from aiolimiter import AsyncLimiter

from app.services.retrieval.rerank.base import logger
from app.services.utils.http import http_retry
from app.utils.env import require_env

TEI_MAX_BATCH = int(os.getenv("TEI_RERANKER_MAX_BATCH", "32"))

_limiter = AsyncLimiter(float(os.getenv("TEI_RERANKER_RPS", "10")), 1)


class TEIReranker:
    """BAAI/bge-reranker-v2-m3 served over a TEI-compatible `/rerank` route."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.model = model
        self.base_url = (base_url or require_env("TEI_RERANKER_BASE_URL")).rstrip("/")
        api_key = api_key or os.getenv("TEI_RERANKER_API_KEY")  # optional for self-hosted
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = httpx.AsyncClient(
            headers=headers, timeout=httpx.Timeout(60.0, connect=10.0)
        )

    async def rank(self, query: str, texts: list[str]) -> list[float]:
        batches = [
            texts[i : i + TEI_MAX_BATCH] for i in range(0, len(texts), TEI_MAX_BATCH)
        ]
        scored = await asyncio.gather(
            *(self._rank_batch(query, batch) for batch in batches)
        )
        return [score for batch in scored for score in batch]

    @http_retry(logger)
    async def _rank_batch(self, query: str, texts: list[str]) -> list[float]:
        async with _limiter:
            r = await self.client.post(
                f"{self.base_url}/rerank",
                json={"query": query, "texts": texts, "truncate": True},
            )
        r.raise_for_status()
        scores = [0.0] * len(texts)
        for item in r.json():
            scores[item["index"]] = item["score"]
        return scores
