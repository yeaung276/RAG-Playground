from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from app.schemas.agent import KnowledgeConfig
from app.schemas.base import CamelModel
from app.schemas.dataset import DatasetStatus
from app.services.retrieval.document import IndexingConfig


class Metric(StrEnum):
    CONTEXT_PRECISION = "context_precision"
    CONTEXT_RECALL = "context_recall"
    HIT_RATE = "hit_rate"
    MRR = "mrr"


class ExperimentCreate(CamelModel):
    dataset_id: str
    knowledge_id: str | None = None
    indexing_config: IndexingConfig | None = None
    knowledge_config: KnowledgeConfig
    metrics: list[Metric] = Field(min_length=1)

    @model_validator(mode="after")
    def _new_base_needs_indexing(self) -> "ExperimentCreate":
        if self.knowledge_id is None and self.indexing_config is None:
            raise ValueError("indexing is required when no knowledge_id is given")
        return self


class ExperimentRead(CamelModel):
    id: str
    dataset_id: str
    knowledge_id: str | None
    indexing_config: IndexingConfig | None
    knowledge_config: KnowledgeConfig
    metrics: list[Metric]
    status: DatasetStatus
    error: str | None
    created_at: datetime
    updated_at: datetime


class ExperimentPage(CamelModel):
    items: list[ExperimentRead]
    total: int
    page: int
    page_size: int
