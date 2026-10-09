import asyncio
import os
import time

import httpx
from aiolimiter import AsyncLimiter
from qdrant_client import AsyncQdrantClient, models

from app.metrics import (
    model_batch_size,
    model_rate_limit_wait_seconds,
    model_request_duration_seconds,
    model_request_errors_total,
)
from app.services.models.rerank.base import logger
from app.services.utils.http import http_retry
from app.utils.env import require_env

TEI_MAX_BATCH = int(os.getenv("TEI_LATE_INTERACTION_MAX_BATCH", "8"))

_limiter = AsyncLimiter(float(os.getenv("TEI_LATE_INTERACTION_RPS", "10")), 1)


class TEILateInteractionReranker:
    """Per-token embeddings over a TEI-compatible `/embed_all` route. Embeds like a
    bi-encoder (one multivector per text) and ranks like a reranker."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.model = model
        self.base_url = (base_url or require_env("TEI_LATE_INTERACTION_BASE_URL")).rstrip("/")
        api_key = api_key or os.getenv("TEI_LATE_INTERACTION_API_KEY")  # optional for self-hosted
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = httpx.AsyncClient(
            headers=headers, timeout=httpx.Timeout(60.0, connect=10.0)
        )
        self.qdrant: AsyncQdrantClient | None = None
        self.kb_id: str | None = None
        self.vector_name: str | None = None

    def update_context(
        self, qdrant: AsyncQdrantClient, kb_id: str, vector_name: str
    ) -> None:
        """Point `rank` at the collection and multivector holding the stored vectors."""
        self.qdrant = qdrant
        self.kb_id = kb_id
        self.vector_name = vector_name

    async def embed(self, texts: list[str]) -> list[list[list[float]]]:
        batches = [
            texts[i : i + TEI_MAX_BATCH] for i in range(0, len(texts), TEI_MAX_BATCH)
        ]
        embedded = await asyncio.gather(
            *(self._embed_batch(batch) for batch in batches)
        )
        return [vectors for batch in embedded for vectors in batch]

    async def rank(
        self, query: str, texts: list[str], chunk_ids: list[str]
    ) -> list[float]:
        if self.qdrant is None or self.kb_id is None or self.vector_name is None:
            raise RuntimeError("Call update_context before rank")
        found = await self.qdrant.query_points(
            self.kb_id,
            query=(await self.embed([query]))[0],
            using=self.vector_name,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="own_chunk_id", match=models.MatchAny(any=chunk_ids)
                    )
                ]
            ),
            limit=len(chunk_ids),
            with_payload=["own_chunk_id"],
        )
        scores = {point.payload["own_chunk_id"]: point.score for point in found.points}
        return [scores.get(chunk_id, 0.0) for chunk_id in chunk_ids]

    @http_retry(logger)
    async def _embed_batch(self, texts: list[str]) -> list[list[list[float]]]:
        model_batch_size.labels(self.model, "late_interaction").observe(len(texts))
        waited = time.perf_counter()
        async with _limiter:
            model_rate_limit_wait_seconds.labels(self.model, "late_interaction").observe(
                time.perf_counter() - waited
            )
            with (
                model_request_duration_seconds.labels(self.model, "late_interaction").time(),
                model_request_errors_total.labels(
                    self.model, "late_interaction"
                ).count_exceptions(),
            ):
                r = await self.client.post(
                    f"{self.base_url}/embed_all", json={"inputs": texts}
                )
                r.raise_for_status()
        return r.json()
