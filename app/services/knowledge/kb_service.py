from qdrant_client import AsyncQdrantClient, models
from sqlalchemy import delete as sa_delete, func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.node import Node
from app.models.kb import KnowledgeBase
from app.schemas.knowledge import KnowledgeBaseRead
from app.services.models.model_service import ModelService
from app.services.retrieval.document import KbConfig, LateInteractionReranker, VectorIndex
from app.services.errors import NotFoundError


class KnowledgeBaseService:
    """CRUD for knowledge bases."""

    def __init__(
        self, session: AsyncSession, qdrant: AsyncQdrantClient, model_service: ModelService
    ):
        self.session = session
        self.qdrant = qdrant
        self.model_service = model_service

    async def create(
        self, name: str, config: KbConfig
    ) -> KnowledgeBaseRead:
        kb = KnowledgeBase(name=name, config=config.model_dump())
        self.session.add(kb)
        await self.session.flush()
        await self._create_collection(kb.id, config)
        await self.session.commit()
        await self.session.refresh(kb)
        return self._read(kb, 0)

    async def update_config(
        self, kb_id: str, config: KbConfig
    ) -> KnowledgeBaseRead:
        kb = await self.session.get(KnowledgeBase, kb_id)
        if kb is None:
            raise NotFoundError(f"Knowledge base {kb_id} not found")

        if self._collection_config_changed(kb.config, config):
            await self.qdrant.delete_collection(kb_id)
            await self._create_collection(kb_id, config)

        kb.config = config.model_dump()
        await self.session.execute(
            sa_update(Node)
            .where(Node.kb_id == kb_id, Node.status == "completed")
            .values(status="out_of_sync")
        )
        await self.session.commit()
        await self.session.refresh(kb)
        counts = await self._file_counts()
        return self._read(kb, counts.get(kb_id, 0))

    async def list(self) -> list[KnowledgeBaseRead]:
        kbs = (
            await self.session.execute(
                select(KnowledgeBase).order_by(KnowledgeBase.created_at)
            )
        ).scalars().all()
        counts = await self._file_counts()
        return [self._read(kb, counts.get(kb.id, 0)) for kb in kbs]

    async def get(self, kb_id: str) -> KnowledgeBaseRead:
        kb = await self.session.get(KnowledgeBase, kb_id)
        if kb is None:
            raise NotFoundError(f"Knowledge base {kb_id} not found")
        counts = await self._file_counts()
        return self._read(kb, counts.get(kb_id, 0))

    async def delete(self, kb_id: str) -> None:
        kb = await self.session.get(KnowledgeBase, kb_id)
        if kb is None:
            raise NotFoundError(f"Knowledge base {kb_id} not found")
        for model in (Chunk, Node):
            await self.session.execute(sa_delete(model).where(model.kb_id == kb_id))
        await self.session.execute(
            sa_delete(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        await self.qdrant.delete_collection(kb_id)
        await self.session.commit()

    async def _file_counts(self) -> dict[str, int]:
        rows = (
            await self.session.execute(
                select(Node.kb_id, func.count())
                .where(Node.type == "file")
                .group_by(Node.kb_id)
            )
        ).all()
        return {kb_id: count for kb_id, count in rows}

    def _read(self, kb: KnowledgeBase, file_count: int) -> KnowledgeBaseRead:
        return KnowledgeBaseRead(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            config=KbConfig(**(kb.config or {})),
            file_count=file_count,
            created_at=kb.created_at,
        )

    async def _create_collection(self, kb_id: str, config: KbConfig) -> None:
        vectors_config = {
            index.vector_name: models.VectorParams(
                size=await self._dimension_of(index.model_id),
                distance=models.Distance.COSINE,
            )
            for index in config.index_types
            if isinstance(index, VectorIndex)
        }
        
        # Special case for late-interaction embedder
        if isinstance(config.reranker, LateInteractionReranker):
            reranker = await self.model_service.resolve_model(config.reranker.model_id)
            vectors_config[config.reranker.model_id] = models.VectorParams(
                size=len((await reranker.embed(["dimension probe"]))[0][0]),
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM
                ),
                # rerank-only, never searched, so skip building the graph index
                hnsw_config=models.HnswConfigDiff(m=0),
            )

        await self.qdrant.create_collection(
            kb_id,
            vectors_config=vectors_config,
            sparse_vectors_config={
                index.vector_name: models.SparseVectorParams(modifier=models.Modifier.IDF)
                for index in config.index_types
                if not isinstance(index, VectorIndex)
            },
        )

        await self.qdrant.create_payload_index(
            kb_id, "chunk_id", field_schema=models.PayloadSchemaType.KEYWORD
        )
        
        await self.qdrant.create_payload_index(
            kb_id, "node_id", field_schema=models.PayloadSchemaType.KEYWORD
        )

        await self.qdrant.create_payload_index(
            kb_id, "parent", field_schema=models.PayloadSchemaType.BOOL
        )

        await self.qdrant.create_payload_index(
            kb_id, "own_chunk_id", field_schema=models.PayloadSchemaType.KEYWORD
        )

    async def _dimension_of(self, model_id: str) -> int:
        """Dense size is fixed at creation and not stored on the model, so embed once to learn it."""
        embedder = await self.model_service.resolve_model(model_id)
        return len((await embedder.embed(["dimension probe"]))[0])

    def _collection_config_changed(
        self, before: dict | None, after: KbConfig
    ) -> bool:
        """Vector size and sparse layout are both fixed at creation."""
        names = {index.vector_name for index in KbConfig(**(before or {})).index_types}
        return names != {index.vector_name for index in after.index_types}
