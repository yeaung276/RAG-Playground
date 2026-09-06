from dataclasses import dataclass
from typing import Literal

from qdrant_client import AsyncQdrantClient, models
from sqlalchemy import select

from app.logger import get_logger
from app.models.chunk import Chunk as ChunkRow
from app.models.kb import KnowledgeBase
from app.services.errors import ConflictError, NotFoundError
from app.services.retrieval.document import IndexTypes, RerankTypes
from app.services.retrieval.embedding import (
    Bm25Embedder,
    Embedder,
    OpenAIEmbedder,
    TEIEmbedder,
)
from app.services.retrieval.rerank import Reranker, TEIReranker

logger = get_logger(__name__)


@dataclass
class Retrieved:
    """A parent chunk surfaced for a query, paired with its similarity score."""

    chunk_id: str
    score: float = 0
    matched_text: str = ""
    chunk: ChunkRow | None = None


class RetrievalService:
    def __init__(self, session_maker, qdrant: AsyncQdrantClient):
        self.session_maker = session_maker
        self.qdrant = qdrant

    async def retrieve(
        self,
        kb_id: str,
        query: str,
        *,
        index_types: list[IndexTypes],
        top_k: int = 5,
        rerank_on: Literal["parent", "child"] | None = None,
        rerank_model: RerankTypes = "BAAI/bge-reranker-v2-m3",
        rerank_pool: int | None = None,
        prefetch_limit: int | None = None,
    ) -> list[Retrieved]:
        """Embed the query, match the nearest child embeddings, and resolve each
        to its parent chunk (small-to-big). Returns up to top_k distinct parents,
        best-scoring first."""

        # defaults parameters
        rerank_pool = rerank_pool or top_k
        prefetch_limit = prefetch_limit or rerank_pool * 2

        async with self.session_maker() as session:
            kb = await session.get(KnowledgeBase, kb_id)
            if kb is None:
                raise NotFoundError(f"Knowledge base {kb_id} not found")

        if not self._is_index_supported(kb, index_types):
            raise ConflictError(
                f"One of the index types is not supported by knowledge base {kb_id}"
            )

        hits = await self._scan_points(
            kb_id, query, index_types, prefetch_limit, limit=rerank_pool
        )
        if not hits:
            return []

        if not rerank_on:
            return await self._hydrate_parents(hits[:top_k])

        hits = await self._hydrate_parents(hits)
        return (await self._rerank(query, hits, rerank_on, rerank_model))[:top_k]

    def _get_embedding_model_from_config(
        self, index_types: list[IndexTypes]
    ) -> dict[IndexTypes, Embedder]:
        """Resolve index types to their backing adapters."""
        embedders: dict[IndexTypes, Embedder] = {}
        for index_type in index_types:
            match index_type:
                case "BAAI/bge-m3":
                    embedders[index_type] = TEIEmbedder(index_type)
                case "text-embedding-3-small" | "text-embedding-3-large":
                    embedders[index_type] = OpenAIEmbedder(index_type)
                case "bm25":
                    embedders[index_type] = Bm25Embedder(index_type)
                case _:
                    raise ValueError(f"Unsupported index type: {index_type!r}")
        return embedders

    def _get_reranker_from_config(self, rerank_model: RerankTypes) -> Reranker:
        """Resolve a rerank model to its backing adapter."""
        match rerank_model:
            case "BAAI/bge-reranker-v2-m3":
                return TEIReranker(rerank_model)
            case _:
                raise ValueError(f"Unsupported rerank model: {rerank_model!r}")

    def _is_index_supported(
        self, kb: KnowledgeBase, index_types: list[IndexTypes]
    ) -> bool:
        if set(index_types) - set((kb.config or {}).get("index_types", [])):
            return False
        return True

    async def _scan_points(
        self,
        kb_id: str,
        query: str,
        index_types: list[IndexTypes],
        prefetch_limit: int,
        limit: int,
    ):
        embedders = self._get_embedding_model_from_config(index_types)
        prefetch = [
            models.Prefetch(
                query=(await embedder.embed([query]))[0],
                using=index_type,
                limit=prefetch_limit,
            )
            for index_type, embedder in embedders.items()
        ]

        single = prefetch[0] if len(prefetch) == 1 else None
        found = await self.qdrant.query_points_groups(
            kb_id,
            group_by="chunk_id",
            prefetch=None if single else prefetch,
            query=(
                single.query if single else models.FusionQuery(fusion=models.Fusion.RRF)
            ),
            using=single.using if single else None,
            limit=limit,
            group_size=1,
            with_payload=["content"],
        )
        return [
            Retrieved(
                chunk_id=str(group.id),
                score=group.hits[0].score,
                matched_text=group.hits[0].payload["content"],
            )
            for group in found.groups
        ]

    async def _hydrate_parents(self, retrieved: list[Retrieved]):
        async with self.session_maker() as session:
            chunks = (
                (
                    await session.execute(
                        select(ChunkRow).where(ChunkRow.id.in_([c.chunk_id for c in retrieved]))
                    )
                )
                .scalars()
                .all()
            )

        by_id = {c.id: c for c in chunks}
        for c in retrieved:
            c.chunk = by_id.get(c.chunk_id, None)
        return retrieved
        
    async def _rerank(
        self,
        query: str,
        retrieved: list[Retrieved],
        rerank_on: Literal["parent", "child"],
        rerank_model: RerankTypes,
    ) -> list[Retrieved]:
        """Rescore hits with a cross-encoder, best first. A hit whose text is
        missing scores 0 and sinks to the bottom."""
        reranker = self._get_reranker_from_config(rerank_model)
        texts = [
            (hit.chunk.content if hit.chunk else "")
            if rerank_on == "parent"
            else hit.matched_text
            for hit in retrieved
        ]
        scores = await reranker.rank(query, texts)
        for hit, score in zip(retrieved, scores):
            hit.score = score
        return sorted(retrieved, key=lambda hit: hit.score, reverse=True)
