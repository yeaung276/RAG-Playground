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

_limiter = AsyncLimiter(float(os.getenv("OPENAI_EMBEDDING_RPS", "10")), 1)

class OpenAIEmbedder:
    """text-embedding-3-* served over an OpenAI-compatible `/embeddings` route."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.model = model
        self.base_url = (base_url or require_env("OPENAI_BASE_URL")).rstrip("/")
        self.api_key = api_key or require_env("OPENAI_API_KEY")
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=httpx.Timeout(60.0, connect=10.0),
        )

    @http_retry(logger)
    async def embed(self, texts: list[str]) -> list[list[float]]:
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
                r = await self.client.post(
                    f"{self.base_url}/embeddings",
                    json={"model": self.model, "input": texts},
                )
                r.raise_for_status()
        data = sorted(r.json()["data"], key=lambda d: d["index"])
        return [d["embedding"] for d in data]
