import asyncio

from fastapi import UploadFile
from sqlalchemy import delete as sa_delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.ids import new_id
from app.models.chunk import Chunk
from app.models.kb import KnowledgeBase
from app.models.node import Node
from app.schemas.knowledge import ChunkRead, FileDetail, NodeRead
from app.services.errors import ConflictError, NotFoundError
from app.storage import Storage


def _sort_key(node: Node) -> tuple[bool, str]:
    # Folders first, then case-insensitive by name.
    return (node.type != "folder", node.name.lower())


class FileService:
    """Owns a knowledge base's file tree: the hierarchy in the DB, the bytes
    in blob `Storage`."""

    def __init__(self, session: AsyncSession, storage: Storage):
        self.session = session
        self.storage = storage

    async def create_folder(
        self, kb_id: str, parent_id: str | None, name: str
    ) -> NodeRead:
        node = Node(kb_id=kb_id, parent_id=parent_id, name=name, type="folder")
        self.session.add(node)
        await self.session.commit()
        await self.session.refresh(node)
        return NodeRead.model_validate(node)

    async def upload_files(
        self, kb_id: str, parent_id: str | None, files: list[UploadFile]
    ) -> list[NodeRead]:
        config = await self._kb_config(kb_id)

        async def upload(f: UploadFile) -> Node:
            data = await f.read()
            key = f"{kb_id}/{new_id()}"
            await self.storage.save(data, key)
            return Node(
                kb_id=kb_id,
                parent_id=parent_id,
                name=f.filename or "unnamed",
                type="file",
                size=len(data),
                mime_type=f.content_type,
                storage_key=key,
                status="processing",
                config=config,
            )
            
        try:
            nodes = await asyncio.gather(*(upload(f) for f in files))
            self.session.add_all(nodes)
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            names = ", ".join(sorted({f.filename or "unnamed" for f in files}))
            raise ConflictError(
                f"A file or folder named {names} already exists in this folder. "
                "Rename it or delete the existing one before re-uploading."
            )
        await self.session.commit()

        return [NodeRead.model_validate(n) for n in nodes]

    async def list_nodes(self, kb_id: str, parent_id: str | None) -> list[NodeRead]:
        rows = (
            (
                await self.session.execute(
                    select(Node).where(Node.kb_id == kb_id, Node.parent_id == parent_id)
                )
            )
            .scalars()
            .all()
        )
        return [NodeRead.model_validate(n) for n in sorted(rows, key=_sort_key)]

    async def get_file_detail(self, kb_id: str, node_id: str) -> FileDetail:
        node = await self._get_node(kb_id, node_id)
        if node.type != "file":
            raise NotFoundError(f"File {node_id} not found")
        rows = (
            (
                await self.session.execute(
                    select(Chunk).where(Chunk.node_id == node_id).order_by(Chunk.seq)
                )
            )
            .scalars()
            .all()
        )
        detail = FileDetail.model_validate(node)
        detail.chunks = [ChunkRead.model_validate(c) for c in rows]
        return detail

    async def read_file(self, kb_id: str, node_id: str) -> tuple[str, str, bytes]:
        node = await self._get_node(kb_id, node_id)
        if node.type != "file" or not node.storage_key:
            raise NotFoundError(f"File {node_id} not found")
        buf = await self.storage.load(node.storage_key)
        return node.name, node.mime_type or "application/octet-stream", buf.read()

    async def resync_node(self, kb_id: str, node_id: str) -> NodeRead:
        node = await self._get_node(kb_id, node_id)
        if node.type != "file":
            raise NotFoundError(f"File {node_id} not found")
        node.config = await self._kb_config(kb_id)
        node.status = "processing"
        node.error = None
        await self.session.commit()
        await self.session.refresh(node)
        return NodeRead.model_validate(node)

    async def delete_node(self, kb_id: str, node_id: str) -> list[str]:
        node = await self._get_node(kb_id, node_id)
        if node.type == "folder":
            child = (
                await self.session.execute(
                    select(Node.id).where(Node.parent_id == node_id).limit(1)
                )
            ).first()
            if child is not None:
                raise ConflictError("Folder not empty")
        await self.session.execute(sa_delete(Chunk).where(Chunk.node_id == node_id))
        await self.session.execute(sa_delete(Node).where(Node.id == node_id))
        await self.session.commit()
        return [node.storage_key] if node.storage_key else []

    async def _get_node(self, kb_id: str, node_id: str) -> Node:
        node = await self.session.get(Node, node_id)
        if node is None or node.kb_id != kb_id:
            raise NotFoundError(f"Node {node_id} not found")
        return node

    async def _kb_config(self, kb_id: str) -> dict | None:
        """The parent KB's config snapshot to stamp onto its files."""
        kb = await self.session.get(KnowledgeBase, kb_id)
        if kb is None:
            raise NotFoundError(f"Knowledge base {kb_id} not found")
        return kb.config
