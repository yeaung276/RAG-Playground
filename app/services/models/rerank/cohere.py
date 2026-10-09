import httpx

from app.metrics import (
    model_batch_size,
    model_request_duration_seconds,
    model_request_errors_total,
)
from app.services.models.rerank.base import logger
from app.services.utils.http import http_retry

COHERE_BASE_URL = "https://api.cohere.com/v2/rerank"


class CohereReranker:
    """Any server speaking the Cohere `/rerank` body: Cohere, Jina, Infinity, vLLM."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.model = model
        self.base_url = (base_url or COHERE_BASE_URL).rstrip("/")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = httpx.AsyncClient(
            headers=headers, timeout=httpx.Timeout(60.0, connect=10.0)
        )

    @http_retry(logger)
    async def rank(
        self, query: str, texts: list[str], chunk_ids: list[str]
    ) -> list[float]:
        model_batch_size.labels(self.model, "rerank").observe(len(texts))
        with (
            model_request_duration_seconds.labels(self.model, "rerank").time(),
            model_request_errors_total.labels(self.model, "rerank").count_exceptions(),
        ):
            r = await self.client.post(
                self.base_url,
                json={"model": self.model, "query": query, "documents": texts},
            )
            r.raise_for_status()
        scores = [0.0] * len(texts)
        for item in r.json()["results"]:
            scores[item["index"]] = item["relevance_score"]
        return scores
