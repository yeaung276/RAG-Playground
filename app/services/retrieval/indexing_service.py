import asyncio
import uuid
from itertools import batched

from qdrant_client import AsyncQdrantClient, models

from app.logger import get_logger
from app.models.chunk import Chunk as ChunkRow
from app.services.retrieval.chunking import (
    Chunker,
    FixedSizeChunker,
    RecursiveChunker,
    SemanticChunker,
)
from app.services.models.embedding import Bm25Embedder, Embedder
from app.services.models.model_service import ModelService
from app.services.retrieval.document import Document, KbConfig, LateInteractionReranker

logger = get_logger(__name__)

# a multivector point is megabytes of JSON; keeps each request under Qdrant's 32 MB cap
UPSERT_BATCH = 4


class IndexingService:
    def __init__(self, session_maker, qdrant: AsyncQdrantClient):
        self.session_maker = session_maker
        self.qdrant = qdrant

    async def create_index(
        self,
        document: Document,
        config: KbConfig,
        *,
        node_id: str,
        kb_id: str,
    ) -> None:
        """Chunk a document, embed its child chunks, and persist parents (chunk
        table) + children (the KB's Qdrant collection). Opens and commits its own
        session, holding it open until the upsert lands."""
        chunker, embedders = await self.resolve_models(config)
        await self.create_index_with(
            document,
            config,
            chunker=chunker,
            embedders=embedders,
            node_id=node_id,
            kb_id=kb_id,
        )

    async def resolve_models(
        self, config: KbConfig
    ) -> tuple[Chunker, dict[str, Embedder]]:
        """Build the config's chunker and embedders."""
        return (
            await self._get_chunker_from_config(config),
            await self._get_embedding_model_from_config(config),
        )

    async def create_index_with(
        self,
        document: Document,
        config: KbConfig,
        *,
        chunker: Chunker,
        embedders: dict[str, Embedder],
        node_id: str,
        kb_id: str,
    ) -> None:
        """`create_index` with models already built by `resolve_models`."""

        # chunking is sync + blocking (splitters, and semantic does sync HTTP)
        corpus = await asyncio.to_thread(chunker.chunk, document)
        texts = [c.content for c in corpus.children]
        vectors = {
            index_type: await embedder.embed(texts)
            for index_type, embedder in embedders.items()
        }
        parent_vectors = (
            await embedders[config.reranker.model_id].embed(
                [p.content for p in corpus.parents]
            )
            if isinstance(config.reranker, LateInteractionReranker)
            else []
        )

        async with self.session_maker() as session:
            pages_by_parent = {}
            for seq, parent in enumerate(corpus.parents):
                pages_by_parent[parent.id] = parent.metadata.get("pages", [])
                session.add(
                    ChunkRow(
                        id=parent.id,
                        node_id=node_id,
                        kb_id=kb_id,
                        seq=seq,
                        content=parent.content,
                        meta={**parent.metadata, "source": document.source},
                    )
                )
            await session.flush()
            points = [
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector={
                        index_type: embedded[i]
                        for index_type, embedded in vectors.items()
                    },
                    payload={
                        "chunk_id": child.parent_id,
                        "own_chunk_id": child.id,
                        "node_id": node_id,
                        "content": child.content,
                        "source": document.source,
                        "pages": pages_by_parent.get(child.parent_id, []),
                        "parent": False,
                    },
                )
                for i, child in enumerate(corpus.children)
            ] + [
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector={config.reranker.model_id: embedded},
                    payload={
                        "chunk_id": parent.id,
                        "own_chunk_id": parent.id,
                        "node_id": node_id,
                        "parent": True,
                    },
                )
                for parent, embedded in zip(corpus.parents, parent_vectors)
            ]
            for batch in batched(points, UPSERT_BATCH):
                await self.qdrant.upsert(kb_id, points=list(batch))
            await session.commit()

        logger.info(
            "Indexed node %s: %d parent(s), %d child embedding(s)",
            node_id,
            len(corpus.parents),
            len(corpus.children),
        )

    async def delete_index(self, *, node_id: str, kb_id: str) -> None:
        """Drop a node's child embeddings from the KB's Qdrant collection."""
        await self.qdrant.delete(
            kb_id,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="node_id", match=models.MatchValue(value=node_id)
                        )
                    ]
                )
            ),
        )

    async def _get_embedding_model_from_config(
        self, config: KbConfig
    ) -> dict[str, Embedder]:
        """Resolve the config's index types, plus a late-interaction reranker, to
        their backing adapters."""
        embedders: dict[str, Embedder] = {}
        async with self.session_maker() as session:
            for index in config.index_types:
                match index.type:
                    case "bm25":
                        embedders[index.vector_name] = Bm25Embedder()
                    case "vector":
                        embedders[index.vector_name] = await ModelService(
                            session
                        ).resolve_model(index.model_id)
                    case _:
                        raise ValueError(f"Unsupported index type: {index!r}")
            if isinstance(config.reranker, LateInteractionReranker):
                embedders[config.reranker.model_id] = await ModelService(
                    session
                ).resolve_model(config.reranker.model_id)
        return embedders

    async def _get_chunker_from_config(self, config: KbConfig) -> Chunker:
        """Resolve the config's chunking method to its backing chunker."""
        match config.chunking_method:
            case "fix-sized":
                return FixedSizeChunker(config.max_chunk_size)
            case "recursive":
                return RecursiveChunker(config.max_chunk_size)
            case "semantic":
                async with self.session_maker() as session:
                    embedder = await ModelService(session).resolve_model(
                        config.chunking_model_id
                    )
                return SemanticChunker(
                    config.max_chunk_size, config.min_chunk_size, embedder
                )
            case _:
                raise ValueError(
                    f"Unsupported chunking method: {config.chunking_method!r}"
                )