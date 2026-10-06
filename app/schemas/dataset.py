from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.base import CamelModel

SLUG = r"^[a-z0-9-]+$"


class Category(StrEnum):
    """How a question is evolved from its chunk — one per pair, fixed set."""

    SIMPLE = "simple"
    REASONING = "reasoning"
    MULTI_CONTEXT = "multi_context"
    CONDITIONAL = "conditional"


DatasetStatus = Literal["pending", "running", "ready", "failed"]


class DatasetCreate(CamelModel):
    name: str = Field(pattern=SLUG, max_length=48)
    model_id: str
    sample_per_file: int = Field(ge=1, le=10)
    mix: dict[Category, int]
    labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_mix(self):
        total = sum(self.mix.values())
        if total != 100:
            raise ValueError(f"Category mix must add up to 100%, got {total}%")
        return self


class DatasetModel(CamelModel):
    """The model that wrote the pairs, as the dataset screen shows it."""

    id: str
    provider: str
    name: str


class DatasetRead(CamelModel):
    id: str
    name: str
    # Not a column — filled in by the service from the joined `models` row.
    model: DatasetModel | None = None
    sample_per_file: int
    mix: dict[Category, int]
    labels: list[str]
    status: DatasetStatus
    error: str | None
    file_count: int
    parsed_count: int
    pair_count: int
    created_at: datetime
    updated_at: datetime


class DatasetSummary(CamelModel):
    id: str
    name: str
    model_name: str | None
    mix: dict[Category, int]
    labels: list[str]
    status: DatasetStatus
    error: str | None
    file_count: int
    parsed_count: int
    pair_count: int
    created_at: datetime


class DatasetPage(CamelModel):
    items: list[DatasetSummary]
    total: int
    page: int
    page_size: int
