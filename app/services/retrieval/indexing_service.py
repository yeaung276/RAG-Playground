import asyncio
import uuid

from qdrant_client import AsyncQdrantClient, models

from app.logger import get_logger
from app.models.chunk import Chunk as ChunkRow
from app.services.retrieval.chunking import (
    Chunker,
    FixedSizeChunker,
    RecursiveChunker,
    SemanticChunker,
)
from app.services.retrieval.document import Document, IndexTypes, IndexingConfig
from app.services.retrieval.embedding import (
    Bm25Embedder,
    Embedder,
    OpenAIEmbedder,
    TEIEmbedder,
)

logger = get_logger(__name__)


class IndexingService:
    def __init__(self, session_maker, qdrant: AsyncQdrantClient):
        self.session_maker = session_maker
        self.qdrant = qdrant

    async def create_index(
        self,
        document: Document,
        config: IndexingConfig,
        *,
        node_id: str,
        kb_id: str,
    ) -> None:
        """Chunk a document, embed its child chunks, and persist parents (chunk
        table) + children (the KB's Qdrant collection). Opens and commits its own
        session, holding it open until the upsert lands."""
        chunker = self._get_chunker_from_config(config)
        embedders = self._get_embedding_model_from_config(config)

        # chunking is sync + blocking (splitters, and semantic does sync HTTP)
        corpus = await asyncio.to_thread(chunker.chunk, document)
        texts = [c.content for c in corpus.children]
        vectors = {
            index_type: await embedder.embed(texts)
            for index_type, embedder in embedders.items()
        }

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
            await self.qdrant.upsert(
                kb_id,
                points=[
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector={
                            index_type: embedded[i]
                            for index_type, embedded in vectors.items()
                        },
                        payload={
                            "chunk_id": child.parent_id,
                            "node_id": node_id,
                            "content": child.content,
                            "source": document.source,
                            "pages": pages_by_parent.get(child.parent_id, []),
                        },
                    )
                    for i, child in enumerate(corpus.children)
                ],
            )
            await session.commit()

        logger.info(
            "Indexed node %s: %d parent(s), %d child embedding(s)",
            node_id,
            len(corpus.parents),
            len(corpus.children),
        )

    def _get_embedding_model_from_config(
        self, config: IndexingConfig
    ) -> dict[IndexTypes, Embedder]:
        """Resolve the config's index types to their backing adapters."""
        embedders: dict[IndexTypes, Embedder] = {}
        for index_type in config.index_types:
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

    def _get_chunker_from_config(self, config: IndexingConfig) -> Chunker:
        """Resolve the config's chunking method to its backing chunker."""
        match config.chunking_method:
            case "fix-sized":
                return FixedSizeChunker(config.max_chunk_size)
            case "recursive":
                return RecursiveChunker(config.max_chunk_size)
            case "semantic":
                return SemanticChunker(config.max_chunk_size, config.min_chunk_size)
            case _:
                raise ValueError(
                    f"Unsupported chunking method: {config.chunking_method!r}"
                )