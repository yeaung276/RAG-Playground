from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from qdrant_client import AsyncQdrantClient, models
from sqlalchemy import select

from app.logger import get_logger
from app.models.chunk import Chunk as ChunkRow
from app.models.kb import KnowledgeBase
from app.services.errors import ConflictError, NotFoundError
from app.services.models.embedding import Bm25Embedder, Embedder
from app.services.models.model_service import ModelService
from app.services.models.rerank import Reranker
from app.services.retrieval.document import IndexSpec, KbConfig, Retrieved

logger = get_logger(__name__)

HYDE_PROMPT = (
    "Write a short passage that answers the user's question, in the style of a "
    "document that would contain the answer. Reply with the passage only."
)


class RetrievalService:
    def __init__(self, session_maker, qdrant: AsyncQdrantClient):
        self.session_maker = session_maker
        self.qdrant = qdrant

    async def retrieve(
        self,
        kb_id: str,
        query: str,
        *,
        index_types: list[IndexSpec],
        top_k: int = 5,
        rerank_on: Literal["parent", "child"] | None = None,
        rerank_pool: int | None = None,
        prefetch_limit: int | None = None,
        hyde: bool = False,
    ) -> list[Retrieved]:
        """Embed the query, match the nearest child embeddings, and resolve each
        to its parent chunk (small-to-big). Returns up to top_k distinct parents,
        best-scoring first."""
        embedders, reranker, hyde_llm = await self.resolve_models(kb_id)
        if not self._is_index_supported(embedders, index_types):
            raise ConflictError(
                f"One of the index types is not supported by knowledge base {kb_id}"
            )
        if rerank_on and reranker is None:
            raise ConflictError(f"Knowledge base {kb_id} has no reranker configured")
        if hyde and hyde_llm is None:
            raise ConflictError(f"Knowledge base {kb_id} has no HyDE model configured")

        return await self.retrieve_with(
            kb_id,
            query,
            embedders={index.vector_name: embedders[index.vector_name] for index in index_types},
            reranker=reranker if rerank_on else None,
            hyde=hyde_llm if hyde else None,
            top_k=top_k,
            rerank_on=rerank_on,
            rerank_pool=rerank_pool,
            prefetch_limit=prefetch_limit,
        )

    async def resolve_models(
        self, kb_id: str
    ) -> tuple[dict[str, Embedder], Reranker | None, BaseChatModel | None]:
        """Build the KB's configured embedders, reranker and HyDE model."""
        async with self.session_maker() as session:
            kb = await session.get(KnowledgeBase, kb_id)
            if kb is None:
                raise NotFoundError(f"Knowledge base {kb_id} not found")

        config = KbConfig(**(kb.config or {}))
        embedders = await self._get_embedding_model_from_config(config.index_types)
        reranker = await self._get_reranker_from_config(kb_id, config) if config.reranker else None
        hyde_llm = await self._get_hyde_from_config(config) if config.hyde else None
        return embedders, reranker, hyde_llm

    async def retrieve_with(
        self,
        kb_id: str,
        query: str,
        *,
        embedders: dict[str, Embedder],
        reranker: Reranker | None = None,
        hyde: BaseChatModel | None = None,
        top_k: int = 5,
        rerank_on: Literal["parent", "child"] | None = None,
        rerank_pool: int | None = None,
        prefetch_limit: int | None = None,
    ) -> list[Retrieved]:
        """`retrieve` with models already built by `resolve_models`."""

        # defaults parameters
        rerank_pool = rerank_pool or top_k
        prefetch_limit = prefetch_limit or rerank_pool * 2

        search_text = await self._hypothesize(query, hyde) if hyde else query
        hits = await self._scan_points(
            kb_id, search_text, embedders, prefetch_limit, limit=rerank_pool
        )
        if not hits:
            return []

        if not rerank_on:
            return await self._hydrate_parents(hits[:top_k])

        hits = await self._hydrate_parents(hits)
        return (await self._rerank(query, hits, rerank_on, reranker))[:top_k]

    async def _get_embedding_model_from_config(
        self, index_types: list[IndexSpec]
    ) -> dict[str, Embedder]:
        """Resolve index types to their backing adapters."""
        embedders: dict[str, Embedder] = {}
        async with self.session_maker() as session:
            for index in index_types:
                match index.type:
                    case "bm25":
                        embedders[index.vector_name] = Bm25Embedder()
                    case "vector":
                        embedders[index.vector_name] = await ModelService(
                            session
                        ).resolve_model(index.model_id)
                    case _:
                        raise ValueError(f"Unsupported index type: {index!r}")
        return embedders

    async def _get_reranker_from_config(self, kb_id: str, config: KbConfig) -> Reranker:
        """Resolve the KB's reranker to its backing adapter."""
        match config.reranker.type:
            case "cross-encoder":
                async with self.session_maker() as session:
                    return await ModelService(session).resolve_model(
                        config.reranker.model_id
                    )
            case "late-interaction":
                async with self.session_maker() as session:
                    reranker = await ModelService(session).resolve_model(
                        config.reranker.model_id
                    )
                reranker.update_context(self.qdrant, kb_id, config.reranker.model_id)
                return reranker
            case _:
                raise ValueError(f"Unsupported reranker: {config.reranker.type!r}")

    async def _get_hyde_from_config(self, config: KbConfig) -> BaseChatModel:
        """Resolve the KB's HyDE model to its chat model."""
        async with self.session_maker() as session:
            llm = await ModelService(session).resolve_model(config.hyde.model_id)
        if not isinstance(llm, BaseChatModel):
            raise ConflictError("HyDE needs a decoder model")
        return llm

    async def _hypothesize(self, query: str, llm: BaseChatModel) -> str:
        """Write a hypothetical answer passage to search with in place of the query."""
        reply = await llm.ainvoke([SystemMessage(HYDE_PROMPT), HumanMessage(query)])
        return reply.text

    def _is_index_supported(
        self, embedders: dict[str, Embedder], index_types: list[IndexSpec]
    ) -> bool:
        available = embedders.keys()
        if {index.vector_name for index in index_types} - available:
            return False
        return True

    async def _scan_points(
        self,
        kb_id: str,
        query: str,
        embedders: dict[str, Embedder],
        prefetch_limit: int,
        limit: int,
    ):
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
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="parent", match=models.MatchValue(value=False)
                    )
                ]
            ),
            limit=limit,
            group_size=1,
            with_payload=["content", "own_chunk_id"],
        )
        return [
            Retrieved(
                chunk_id=str(group.id),
                score=group.hits[0].score,
                matched_text=group.hits[0].payload["content"],
                matched_chunk_id=group.hits[0].payload["own_chunk_id"],
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
        reranker: Reranker,
    ) -> list[Retrieved]:
        """Rescore hits with a cross-encoder, best first. A hit whose text is
        missing scores 0 and sinks to the bottom."""
        texts = [
            (hit.chunk.content if hit.chunk else "")
            if rerank_on == "parent"
            else hit.matched_text
            for hit in retrieved
        ]
        chunk_ids = [
            hit.chunk_id if rerank_on == "parent" else hit.matched_chunk_id
            for hit in retrieved
        ]
        scores = await reranker.rank(query, texts, chunk_ids)
        for hit, score in zip(retrieved, scores):
            hit.score = score
        return sorted(retrieved, key=lambda hit: hit.score, reverse=True)
