from app.logger import get_logger
from app.models.node import Node
from app.services.retrieval.document import KbConfig
from app.services.retrieval.extraction_service import ExtractionService
from app.services.retrieval.indexing_service import IndexingService
from app.storage import Storage

logger = get_logger(__name__)

_MAX_ERROR_LEN = 2000


class FileProcessor:
    def __init__(
        self,
        storage: Storage,
        extraction: ExtractionService,
        indexing: IndexingService,
        session_maker,
    ):
        self.storage = storage
        self.extraction = extraction
        self.indexing = indexing
        self.session_maker = session_maker

    async def process(self, node_id: str) -> None:
        """OCR a file node's bytes, index them, and record the outcome."""
        try:
            node = await self._load(node_id)
            if node is None or node.type != "file" or not node.storage_key:
                logger.warning(
                    "Indexing skipped: node %s missing or not a stored file", node_id
                )
                return

            if not self.extraction.is_supported(node.mime_type):
                logger.warning(
                    "Indexing skipped: node %s has unsupported mime %s",
                    node_id,
                    node.mime_type,
                )
                await self._save(
                    node_id,
                    status="failed",
                    error=f"Unsupported file type: {node.mime_type}",
                )
                return

            try:
                logger.info("Extracting contents from file %s", node.storage_key)
                buf = await self.storage.load(node.storage_key)
                document = await self.extraction.process(
                    buf, node.mime_type, name=node.storage_key
                )

                logger.info(
                    "Indexing file %s with config %s", node.storage_key, node.config
                )
                config = KbConfig(**(node.config or {}))
                await self.indexing.create_index(
                    document, config, node_id=node_id, kb_id=node.kb_id
                )
                await self._save(
                    node_id, status="completed", content=document.model_dump(mode="json")
                )
                logger.info("Indexed node %s (%d page(s))", node_id, len(document.pages))
            except Exception as exc:  # noqa: BLE001 — surface failure to the user
                await self._save(
                    node_id,
                    status="failed",
                    error=str(exc)[:_MAX_ERROR_LEN] or exc.__class__.__name__,
                )
                logger.exception("Indexing failed for node %s", node_id)
        except Exception:  # noqa: BLE001 — a background task must never crash its caller
            logger.exception("File processing task crashed for node %s", node_id)

    async def delete(self, kb_id: str, node_id: str, storage_keys: list[str]) -> None:
        """Delete the vectors and blob(s) for a removed file node.

        The DB rows are already gone (deleted synchronously in the request);
        this cleans up Qdrant and storage out of band since that IO can be slow.
        It never crashes its caller.
        """
        try:
            await self.indexing.delete_index(node_id=node_id, kb_id=kb_id)
            for key in storage_keys:
                await self.storage.delete(key)
            logger.info(
                "Deleted vectors and %d blob(s) for node %s", len(storage_keys), node_id
            )
        except Exception:  # noqa: BLE001 — a background task must never crash its caller
            logger.exception("Cleanup failed for node %s", node_id)

    async def _load(self, node_id: str) -> Node | None:
        """Brief read: fetch the node, detached, for its OCR/index inputs."""
        async with self.session_maker() as session:
            return await session.get(Node, node_id)

    async def _save(
        self,
        node_id: str,
        *,
        status: str | None,
        error: str | None = None,
        content: dict | None = None,
    ) -> None:
        """Brief write: record the processing outcome on the node."""
        async with self.session_maker() as session:
            node = await session.get(Node, node_id)
            if node is None:
                return
            node.status = status
            node.error = error
            if content is not None:
                node.content = content
            await session.commit()