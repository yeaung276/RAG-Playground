from qdrant_client import AsyncQdrantClient, models
from sqlalchemy import delete as sa_delete, func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.node import Node
from app.models.kb import KnowledgeBase
from app.schemas.knowledge import KnowledgeBaseRead
from app.services.retrieval.document import EMBEDDING_DIMENSIONS, IndexingConfig
from app.services.errors import NotFoundError


class KnowledgeBaseService:
    """CRUD for knowledge bases."""

    def __init__(self, session: AsyncSession, qdrant: AsyncQdrantClient):
        self.session = session
        self.qdrant = qdrant

    async def create(
        self, name: str, config: IndexingConfig
    ) -> KnowledgeBaseRead:
        kb = KnowledgeBase(name=name, config=config.model_dump())
        self.session.add(kb)
        await self.session.flush()
        await self._create_collection(kb.id, config)
        await self.session.commit()
        await self.session.refresh(kb)
        return self._read(kb, 0)

    async def update_config(
        self, kb_id: str, config: IndexingConfig
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
            config=IndexingConfig(**(kb.config or {})),
            file_count=file_count,
            created_at=kb.created_at,
        )

    async def _create_collection(self, kb_id: str, config: IndexingConfig) -> None:
        await self.qdrant.create_collection(
            kb_id,
            vectors_config={
                index_type: models.VectorParams(
                    size=EMBEDDING_DIMENSIONS[index_type],
                    distance=models.Distance.COSINE,
                )
                for index_type in config.index_types
                if index_type in EMBEDDING_DIMENSIONS
            },
            sparse_vectors_config={
                index_type: models.SparseVectorParams(modifier=models.Modifier.IDF)
                for index_type in config.index_types
                if index_type not in EMBEDDING_DIMENSIONS
            },
        )

        await self.qdrant.create_payload_index(
            kb_id, "chunk_id", field_schema=models.PayloadSchemaType.KEYWORD
        )
        
        await self.qdrant.create_payload_index(
            kb_id, "node_id", field_schema=models.PayloadSchemaType.KEYWORD
        )

    def _collection_config_changed(
        self, before: dict | None, after: IndexingConfig
    ) -> bool:
        """Vector size and sparse layout are both fixed at creation."""
        before = before or {}
        return set(before.get("index_types", [])) != set(after.index_types)
