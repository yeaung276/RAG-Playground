import asyncio
import os
import time

import httpx
from aiolimiter import AsyncLimiter

from app.metrics import (
    model_batch_size,
    model_rate_limit_wait_seconds,
    model_request_duration_seconds,
    model_request_errors_total,
)
from app.services.models.embedding.base import logger
from app.services.utils.http import http_retry
from app.utils.env import require_env

TEI_MAX_BATCH = int(os.getenv("TEI_EMBEDDING_MAX_BATCH", "32"))

_limiter = AsyncLimiter(float(os.getenv("TEI_EMBEDDING_RPS", "10")), 1)

class TEIEmbedder:
    """BAAI/bge-m3 served over a TEI-compatible `/embed` route (HF TEI / Infinity)."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.model = model
        self.base_url = (base_url or require_env("TEI_EMBEDDING_BASE_URL")).rstrip("/")
        api_key = api_key or os.getenv("TEI_EMBEDDING_API_KEY")  # optional for self-hosted
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = httpx.AsyncClient(
            headers=headers, timeout=httpx.Timeout(60.0, connect=10.0)
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        batches = [
            texts[i : i + TEI_MAX_BATCH] for i in range(0, len(texts), TEI_MAX_BATCH)
        ]
        embedded = await asyncio.gather(
            *(self._embed_batch(batch) for batch in batches)
        )
        return [vector for batch in embedded for vector in batch]

    @http_retry(logger)
    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        model_batch_size.labels(self.model, "embed").observe(len(texts))
        waited = time.perf_counter()
        async with _limiter:
            model_rate_limit_wait_seconds.labels(self.model, "embed").observe(
                time.perf_counter() - waited
            )
            with (
                model_request_duration_seconds.labels(self.model, "embed").time(),
                model_request_errors_total.labels(self.model, "embed").count_exceptions(),
            ):
                r = await self.client.post(f"{self.base_url}/embed", json={"inputs": texts})
                r.raise_for_status()
        return r.json()
