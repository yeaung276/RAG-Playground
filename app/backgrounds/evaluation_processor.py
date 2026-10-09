import json

from app.logger import get_logger
from app.models.dataset import Dataset
from app.models.experiment import Experiment
from app.models.node import Node
from app.schemas.agent import KnowledgeConfig
from app.schemas.experiment import Metric
from app.services.dataset.evaluation_service import EvaluationService
from app.services.dataset.experiment_service import result_path
from app.services.retrieval.document import Document, KbConfig, Page
from app.services.retrieval.indexing_service import IndexingService
from app.services.retrieval.retrieval_service import RetrievalService
from app.storage import Storage
from app.utils.archive import read_text_files

logger = get_logger(__name__)


class EvaluationProcessor:
    def __init__(
        self,
        storage: Storage,
        indexing: IndexingService,
        retrieval: RetrievalService,
        evaluation: EvaluationService,
        session_maker,
    ):
        self.storage = storage
        self.indexing = indexing
        self.retrieval = retrieval
        self.evaluation = evaluation
        self.session_maker = session_maker

    async def run(self, experiment_id: str, skip_indexing: bool = False) -> None:
        try:
            experiment = await self._get_experiment(experiment_id)
            if not (skip_indexing or experiment.snapshot_retrieval_config["skip_dataset_indexing"]):
                await self._update_experiment(experiment_id, status="importing")
                await self._index_dataset_into_kb(experiment)
            await self._update_experiment(experiment_id, status="running")
            scores = await self._retrieve_and_score(experiment)
            await self._update_experiment(
                experiment_id,
                status="success",
                result_path=result_path(experiment_id),
                scores=scores,
            )
        except Exception as exc:  # noqa: BLE001 — a background task must never crash its caller
            await self._update_experiment(experiment_id, status="failed", error=str(exc)[:2000])
            logger.exception("Evaluation failed for experiment %s", experiment_id)

    async def _index_dataset_into_kb(self, experiment: Experiment) -> None:
        dataset = await self._get_dataset(experiment.dataset_id)
        config = KbConfig(**experiment.snapshot_kb_config)
        chunker, embedders = await self.indexing.resolve_models(config)
        for name, text in read_text_files(await self.storage.load(dataset.source_key)):
            node_id = await self._create_node(experiment.knowledge_id, name, config)
            await self.indexing.create_index_with(
                Document(source=name, pages=[Page(index=0, markdown=text)]),
                config,
                chunker=chunker,
                embedders=embedders,
                node_id=node_id,
                kb_id=experiment.knowledge_id,
            )

    async def _retrieve_and_score(self, experiment: Experiment) -> dict[str, float]:
        dataset = await self._get_dataset(experiment.dataset_id)
        pairs = json.loads((await self.storage.load(dataset.result_key)).read())
        config = KnowledgeConfig(**experiment.snapshot_retrieval_config)
        embedders, reranker = await self.retrieval.resolve_models(
            experiment.knowledge_id, index_types=config.index_types, rerank_on=config.rerank_on
        )
        options = config.model_dump(exclude_none=True, exclude={"index_types"})
        metrics = [Metric(m) for m in experiment.metrics]

        scored = []
        for pair in pairs:
            retrieved = await self.retrieval.retrieve_with(
                experiment.knowledge_id,
                pair["question"],
                embedders=embedders,
                reranker=reranker,
                **options,
            )
            scores, status, highlights = self.evaluation.score(
                retrieved, pair["context"], pair["source_file"], metrics
            )
            scored.append({
                "question": pair["question"],
                "answer": pair["answer"],
                "category": pair["category"],
                "labels": pair["labels"],
                "context": pair["context"],
                "source_file": pair["source_file"],
                "generated_answer": None,
                "retrieved": [
                    {
                        "rank": rank,
                        "chunk_id": hit.chunk_id,
                        "source": (hit.chunk.meta or {}).get("source") if hit.chunk else None,
                        "score": hit.score,
                        "content": hit.chunk.content if hit.chunk else "",
                        "highlights": spans,
                    }
                    for rank, (hit, spans) in enumerate(zip(retrieved, highlights), start=1)
                ],
                "scores": scores,
                "status": status,
            })

        result = {
            "metrics": self.evaluation.average([p["scores"] for p in scored]),
            "pairs": scored,
        }
        await self.storage.save(
            json.dumps(result, ensure_ascii=False, indent=2).encode(), result_path(experiment.id)
        )
        return result["metrics"]

    async def _create_node(self, kb_id: str, name: str, config: KbConfig) -> str:
        async with self.session_maker() as session:
            node = Node(
                kb_id=kb_id, name=name, type="file", mime_type="text/plain",
                config=config.model_dump(), status="completed",
            )
            session.add(node)
            await session.commit()
            return node.id

    async def _get_dataset(self, dataset_id: str) -> Dataset:
        async with self.session_maker() as session:
            return await session.get(Dataset, dataset_id)

    async def _get_experiment(self, experiment_id: str) -> Experiment:
        async with self.session_maker() as session:
            return await session.get(Experiment, experiment_id)

    async def _update_experiment(self, experiment_id: str, **fields) -> None:
        async with self.session_maker() as session:
            experiment = await session.get(Experiment, experiment_id)
            for field, value in fields.items():
                setattr(experiment, field, value)
            await session.commit()
