"""Orchestrates a RAG retrieval evaluation.

For each config: index the corpus into a fresh knowledge base (or reuse an
existing one via --skip-index), stream every eval question through retrieval,
feed each result to every metric, then write a report with per-type breakdowns.

Both loaders stream — questions and documents are read one at a time, never held
in memory in bulk; progress bars are sized by a cheap `total()` scan.

App services are imported at module load, so this module must only be imported
after the env file has been applied (settings + db engine build at import time).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from app.db.qdrant import qdrant
from app.db.session import async_session_maker
from app.logger import get_logger
from app.models.node import Node
from app.services.knowledge.kb_service import KnowledgeBaseService
from app.services.retrieval.document import IndexingConfig
from app.services.retrieval.indexing_service import IndexingService
from app.services.retrieval.retrieval_service import RetrievalService
from commands.eval_utils.rag.dataloaders import build_corpus_loader, build_qa_loader
from commands.eval_utils.rag.metrics import build_metrics
from commands.eval_utils.rag.report import render_report

logger = get_logger(__name__)

# the rest of the config file is indexing, which IndexingConfig parses. These keys
# are query-time instead, and go straight to retrieve() as kwargs.
RETRIEVAL_KEYS = {
    "rerankOn": "rerank_on",
    "rerankModel": "rerank_model",
    "rerankPool": "rerank_pool",
    "prefetchLimit": "prefetch_limit",
}


@dataclass
class EvalOptions:
    dataset: str
    configs: list[tuple[str, dict]]
    metrics: list[str]
    top_ks: list[int]
    output: str
    kb_id: str | None = None
    skip_index: bool = False
    cleanup: bool = False
    limit: int | None = None

    @classmethod
    def from_args(cls, args) -> "EvalOptions":
        configs = []
        for spec in args.config:
            name, _, path = spec.partition("=")
            if not path:
                name, path = Path(name).stem, name
            configs.append((name, json.loads(Path(path).read_text())))
        return cls(
            dataset=args.dataset,
            configs=configs,
            metrics=[m.strip() for m in args.metrics.split(",") if m.strip()],
            top_ks=sorted(int(x) for x in args.top_k.split(",")),
            output=args.output,
            kb_id=args.kb_id,
            skip_index=args.skip_index,
            cleanup=args.cleanup_after_eval,
            limit=args.limit,
        )


class RagEvaluator:
    def __init__(self, options: EvalOptions):
        self.options = options
        self.session_maker = async_session_maker
        self.indexer = IndexingService(async_session_maker, qdrant)
        self.retriever = RetrievalService(async_session_maker, qdrant)

    async def run(self) -> None:
        results = []
        for name, raw in self.options.configs:
            config = IndexingConfig.model_validate(raw)
            retrieval = {
                arg: raw[key] for key, arg in RETRIEVAL_KEYS.items() if key in raw
            }
            kb_id = self.options.kb_id if self.options.skip_index else await self._index(name, config)
            metrics = await self._evaluate(name, config, retrieval, kb_id)
            results.append((name, kb_id, raw, metrics))
            if self.options.cleanup and not self.options.skip_index:
                logger.info("[%s] cleaning up kb %s", name, kb_id)
                await self._cleanup(kb_id)

        report = render_report(results, self.options.output)
        report_path = Path(self.options.output) / "report.md"
        report_path.write_text(report)
        logger.info("Wrote %s", report_path)

    async def _index(self, name: str, config: IndexingConfig) -> str:
        kb_id = await self._create_kb(name, config)
        loader = build_corpus_loader(self.options.dataset)
        with logging_redirect_tqdm():
            bar = tqdm(total=loader.total(), desc=f"index:{name}", unit="doc")
            async for document in loader:
                node_id = await self._create_node(kb_id, document.source)
                await self.indexer.create_index(document, config, node_id=node_id, kb_id=kb_id)
                bar.update(1)
            bar.close()
        return kb_id

    async def _evaluate(self, name: str, config: IndexingConfig, retrieval: dict, kb_id: str):
        metrics = build_metrics(self.options.metrics, self.options.top_ks)
        top_k = max(self.options.top_ks)
        loader = build_qa_loader(self.options.dataset, self.options.limit)
        with logging_redirect_tqdm():
            bar = tqdm(total=loader.total(), desc=f"query:{name}", unit="q")
            async for question in loader:
                retrieved = await self.retriever.retrieve(
                    kb_id,
                    question.question,
                    index_types=config.index_types,
                    top_k=top_k,
                    **retrieval,
                )
                for metric in metrics:
                    metric.add(retrieved, question.relevant, question.type, question.source_doc)
                bar.update(1)
            bar.close()
        return metrics

    async def _create_kb(self, name: str, config: IndexingConfig) -> str:
        async with self.session_maker() as session:
            kb = await KnowledgeBaseService(session, qdrant).create(f"eval:{name}", config)
        return kb.id

    async def _create_node(self, kb_id: str, source: str) -> str:
        async with self.session_maker() as session:
            node = Node(kb_id=kb_id, name=source, type="file")
            session.add(node)
            await session.flush()
            node_id = node.id
            await session.commit()
        return node_id

    async def _cleanup(self, kb_id: str) -> None:
        async with self.session_maker() as session:
            await KnowledgeBaseService(session, qdrant).delete(kb_id)
