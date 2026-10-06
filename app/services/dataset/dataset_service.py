from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.models.model import Model
from app.schemas.dataset import DatasetCreate, DatasetModel, DatasetPage, DatasetRead
from app.services.errors import BadRequestError, ConflictError, NotFoundError
from app.storage import Storage


def source_key(dataset_id: str) -> str:
    return f"datasets/{dataset_id}/source.zip"


def result_key(dataset_id: str) -> str:
    return f"datasets/{dataset_id}/pairs.json"


class DatasetService:
    def __init__(self, session: AsyncSession, storage: Storage):
        self.session = session
        self.storage = storage

    async def create(self, payload: DatasetCreate, archive: UploadFile) -> DatasetRead:
        dataset = Dataset(
            name=payload.name,
            model_id=payload.model_id,
            sample_per_file=payload.sample_per_file,
            mix={c.value: pct for c, pct in payload.mix.items()},
            labels=payload.labels,
            status="pending",
        )
        self.session.add(dataset)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(
                f"A dataset named {payload.name} already exists. "
                "Pick another name or delete the existing one."
            )

        dataset.source_key = source_key(dataset.id)
        await self.storage.save(await archive.read(), dataset.source_key)
        await self.session.commit()
        await self.session.refresh(dataset)
        return await self._read(dataset)

    async def list(self, page: int, page_size: int) -> DatasetPage:
        total = await self.session.scalar(select(func.count()).select_from(Dataset)) or 0
        rows = (
            await self.session.execute(
                select(Dataset, Model)
                .outerjoin(Model, Model.id == Dataset.model_id)
                .order_by(Dataset.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return DatasetPage(
            items=[self._to_read(d, m) for d, m in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get(self, dataset_id: str) -> DatasetRead:
        return await self._read(await self._get(dataset_id))

    async def reset_failed(self, dataset_id: str) -> DatasetRead:
        dataset = await self._get(dataset_id)
        if dataset.status != "failed":
            raise BadRequestError(f"Dataset {dataset_id} is {dataset.status}, not failed")
        dataset.status = "pending"
        dataset.error = None
        await self.session.commit()
        await self.session.refresh(dataset)
        return await self._read(dataset)

    async def read_pairs(self, dataset_id: str) -> tuple[str, bytes]:
        """The generated JSON file, served as-is for the client to render."""
        dataset = await self._get(dataset_id)
        if not dataset.result_key:
            raise NotFoundError(f"Dataset {dataset_id} has no pairs yet")
        buf = await self.storage.load(dataset.result_key)
        return f"{dataset.name}.json", buf.read()

    async def _get(self, dataset_id: str) -> Dataset:
        dataset = await self.session.get(Dataset, dataset_id)
        if dataset is None:
            raise NotFoundError(f"Dataset {dataset_id} not found")
        return dataset

    async def _read(self, dataset: Dataset) -> DatasetRead:
        model = (
            await self.session.get(Model, dataset.model_id) if dataset.model_id else None
        )
        return self._to_read(dataset, model)

    @staticmethod
    def _to_read(dataset: Dataset, model: Model | None) -> DatasetRead:
        read = DatasetRead.model_validate(dataset)
        read.model = (
            DatasetModel(id=model.id, provider=model.provider, name=model.name)
            if model
            else None
        )
        return read
