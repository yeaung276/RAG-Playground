from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.agent import IndexSpec, KnowledgeConfig
from app.schemas.base import CamelModel
from app.services.retrieval.document import KbConfig

ExperimentStatus = Literal["pending", "importing", "running", "success", "failed"]

PairScoreStatus = Literal["full", "partial", "miss"]


class Metric(StrEnum):
    CONTEXT_PRECISION = "context_precision"
    CONTEXT_RECALL = "context_recall"
    HIT_RATE = "hit_rate"
    MRR = "mrr"


class ExperimentCreate(CamelModel):
    dataset_id: str
    knowledge_id: str | None = None
    kb_config: KbConfig | None = None
    retrieval_config: KnowledgeConfig
    metrics: list[Metric] = Field(min_length=1)

    @model_validator(mode="after")
    def _new_base_needs_kb_config(self) -> "ExperimentCreate":
        if self.knowledge_id is None and self.kb_config is None:
            raise ValueError("kb_config is required when no knowledge_id is given")
        return self


class ExperimentRead(CamelModel):
    id: str
    name: str
    dataset_id: str
    knowledge_id: str | None
    kb_config: KbConfig | None
    retrieval_config: KnowledgeConfig
    metrics: list[Metric]
    scores: dict[str, float] | None
    status: ExperimentStatus
    error: str | None
    created_at: datetime
    updated_at: datetime


class ExperimentSummary(CamelModel):
    id: str
    name: str
    index_types: list[IndexSpec]
    top_k: int | None
    rerank_on: Literal["parent", "child"] | None
    metric_count: int
    status: ExperimentStatus
    error: str | None
    created_at: datetime


class ExperimentScores(CamelModel):
    id: str
    name: str
    created_at: datetime
    scores: dict[str, float]


class ExperimentPage(CamelModel):
    items: list[ExperimentSummary]
    total: int
    page: int
    page_size: int
