import json
import random
import zipfile

from langchain_core.language_models import BaseChatModel

from app.logger import get_logger
from app.models.dataset import Dataset
from app.schemas.dataset import Category
from app.services.dataset.dataset_service import result_key
from app.services.dataset.datagen_service import DataGenerationService
from app.services.errors import ConflictError
from app.services.models.model_service import ModelService
from app.storage import Storage

logger = get_logger(__name__)


class DatasetProcessor:
    def __init__(self, storage: Storage, session_maker):
        self.storage = storage
        self.session_maker = session_maker

    async def generate(self, dataset_id: str) -> None:
        try:
            dataset = await self._load(dataset_id)
            if dataset is None or not dataset.source_key:
                logger.warning("Generation skipped: dataset %s has no archive", dataset_id)
                return

            datagen = await self._get_datagen(dataset.model_id)
            buf = await self.storage.load(dataset.source_key)

            with zipfile.ZipFile(buf) as zf:
                files = [n for n in zf.namelist() if not n.endswith("/")]

                logger.info(
                    "Generating %s: %d file(s) x %d pairs, model %s, mix %s, labels %s",
                    dataset.name, len(files), dataset.sample_per_file,
                    dataset.model_id, dataset.mix, dataset.labels,
                )
                await self._save(dataset_id, status="running", file_count=len(files))

                pairs = []
                for parsed, name in enumerate(files, start=1):
                    logger.info("  [%d/%d] %s", parsed, len(files), name)
                    text = zf.read(name).decode("utf-8", errors="ignore")
                    categories = self._weighted_categories(
                        dataset.mix, dataset.sample_per_file
                    )
                    samples = await datagen.create_samples(
                        text, categories, dataset.labels
                    )
                    pairs += [
                        {"source_file": name, **sample.model_dump(mode="json")}
                        for sample in samples
                    ]
                    await self._save(dataset_id, parsed_count=parsed, pair_count=len(pairs))

            key = result_key(dataset_id)
            await self.storage.save(json.dumps(pairs, indent=2).encode(), key)
            await self._save(dataset_id, status="ready", result_key=key)
            logger.info("Generated %s: %d pair(s) at %s", dataset_id, len(pairs), key)
        except Exception as exc:  # noqa: BLE001 — a background task must never crash its caller
            await self._save(dataset_id, status="failed", error=str(exc)[:2000])
            logger.exception("Generation failed for dataset %s", dataset_id)

    async def _get_datagen(self, model_id: str | None) -> DataGenerationService:
        async with self.session_maker() as session:
            llm = await ModelService(session).resolve_model(model_id)
            if not isinstance(llm, BaseChatModel):
                raise ConflictError("A dataset needs a decoder model to generate pairs")
        return DataGenerationService(llm)

    async def _load(self, dataset_id: str) -> Dataset | None:
        async with self.session_maker() as session:
            return await session.get(Dataset, dataset_id)

    async def _save(self, dataset_id: str, **fields) -> None:
        async with self.session_maker() as session:
            dataset = await session.get(Dataset, dataset_id)
            if dataset is None:
                return
            for field, value in fields.items():
                setattr(dataset, field, value)
            await session.commit()

    @staticmethod
    def _weighted_categories(mix: dict[str, int], count: int) -> list[Category]:
        """The per-file category slots, drawn at the percentages the mix asks for."""
        entries = [(Category(c), w) for c, w in mix.items() if w > 0]
        if not entries:
            return [Category.SIMPLE] * count
        categories, weights = zip(*entries)
        return random.choices(categories, weights=weights, k=count)
