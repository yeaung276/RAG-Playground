from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.models.experiment import Experiment
from app.schemas.agent import KnowledgeConfig
from app.schemas.experiment import ExperimentCreate, ExperimentPage, ExperimentRead
from app.services.errors import NotFoundError
from app.services.knowledge.kb_service import KnowledgeBaseService
from app.services.retrieval.document import KbConfig
from app.storage import Storage


def result_path(experiment_id: str) -> str:
    return f"experiments/{experiment_id}/result.json"


class ExperimentationService:
    def __init__(
        self, session: AsyncSession, storage: Storage, kb_service: KnowledgeBaseService
    ):
        self.session = session
        self.storage = storage
        self.kb_service = kb_service

    async def create(self, payload: ExperimentCreate) -> ExperimentRead:
        dataset = await self.session.get(Dataset, payload.dataset_id)
        if dataset is None:
            raise NotFoundError(f"Dataset {payload.dataset_id} not found")

        knowledge_id = payload.knowledge_id
        if knowledge_id is None:
            created = await self.kb_service.create(
                name=f"exp-{dataset.name}", config=payload.kb_config
            )
            knowledge_id = created.id
        kb = await self.kb_service.get(knowledge_id)

        experiment = Experiment(
            dataset_id=dataset.id,
            knowledge_id=kb.id,
            snapshot_retrieval_config={
                **payload.retrieval_config.model_dump(),
                "skip_dataset_indexing": payload.knowledge_id is not None,
            },
            snapshot_kb_config=kb.config.model_dump(),
            metrics=[metric.value for metric in payload.metrics],
            status="pending",
        )
        self.session.add(experiment)
        await self.session.commit()
        await self.session.refresh(experiment)
        return self._to_read(experiment)

    async def list(
        self, page: int, page_size: int, dataset_id: str | None = None
    ) -> ExperimentPage:
        where = [Experiment.dataset_id == dataset_id] if dataset_id else []
        total = (
            await self.session.scalar(
                select(func.count()).select_from(Experiment).where(*where)
            )
            or 0
        )
        rows = (
            (
                await self.session.execute(
                    select(Experiment)
                    .where(*where)
                    .order_by(Experiment.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return ExperimentPage(
            items=[self._to_read(experiment) for experiment in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get(self, experiment_id: str) -> ExperimentRead:
        return self._to_read(await self._get(experiment_id))

    async def read_result(self, experiment_id: str) -> tuple[str, bytes]:
        experiment = await self._get(experiment_id)
        if not experiment.result_path:
            raise NotFoundError(f"Experiment {experiment_id} has no result yet")
        buf = await self.storage.load(experiment.result_path)
        return f"{experiment.id}.json", buf.read()

    async def _get(self, experiment_id: str) -> Experiment:
        experiment = await self.session.get(Experiment, experiment_id)
        if experiment is None:
            raise NotFoundError(f"Experiment {experiment_id} not found")
        return experiment

    @staticmethod
    def _to_read(experiment: Experiment) -> ExperimentRead:
        return ExperimentRead(
            id=experiment.id,
            dataset_id=experiment.dataset_id,
            knowledge_id=experiment.knowledge_id,
            kb_config=KbConfig(**experiment.snapshot_kb_config),
            retrieval_config=KnowledgeConfig(**experiment.snapshot_retrieval_config),
            metrics=experiment.metrics,
            status=experiment.status,
            error=experiment.error,
            created_at=experiment.created_at,
            updated_at=experiment.updated_at,
        )
