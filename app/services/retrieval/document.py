from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.base import CamelModel

# Document
class BlockType(str, Enum):
    TITLE = "title"
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    CHART = "chart"
    FORMULA = "formula"
    OTHER = "other"


class Block(BaseModel):
    type: BlockType
    content: str


class Page(BaseModel):
    index: int
    markdown: str
    blocks: list[Block] = []


class Document(BaseModel):
    source: str = ""
    pages: list[Page] = []


# Chunks
class Chunk(BaseModel):
    id: str
    content: str
    parent_id: str | None = None  # None for parents
    metadata: dict = Field(default_factory=dict)


class Corpus(BaseModel):
    parents: list[Chunk] = []
    children: list[Chunk] = []


# Config
IndexTypes = Literal[
    "BAAI/bge-m3",
    "text-embedding-3-small",
    "text-embedding-3-large",
    "bm25"
]

EMBEDDING_DIMENSIONS: dict[IndexTypes, int] = {
    "BAAI/bge-m3": 1024,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}

RerankTypes = Literal[
    "BAAI/bge-reranker-v2-m3"
]

ChunkingStrategy = Literal[
    "fix-sized",
    "recursive",
    "semantic"
]


class IndexingConfig(CamelModel):
    # chunking config
    chunking_method: ChunkingStrategy = "semantic"
    max_chunk_size: int = Field(default=1024, gt=0)
    min_chunk_size: int = Field(default=256, gt=0)

    # indexing config
    index_types: list[IndexTypes] = Field(default=["bm25"], min_length=1)

    @model_validator(mode="after")
    def _child_smaller_than_parent(self) -> "IndexingConfig":
        if self.min_chunk_size >= self.max_chunk_size:
            raise ValueError("min_chunk_size must be smaller than parent_chunk_size")
        return self