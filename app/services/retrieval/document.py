from enum import Enum
from typing import Annotated, Literal

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
ChunkingStrategy = Literal[
    "fix-sized",
    "recursive",
    "semantic"
]


class Bm25Index(CamelModel):
    type: Literal["bm25"] = "bm25"

    @property
    def vector_name(self) -> str:
        return "bm25"


class VectorIndex(CamelModel):
    type: Literal["vector"] = "vector"
    model_id: str = Field(min_length=1)

    @property
    def vector_name(self) -> str:
        return self.model_id


class CrossEncoderReranker(CamelModel):
    type: Literal["cross-encoder"] = "cross-encoder"
    model_id: str = Field(min_length=1)


class LateInteractionReranker(CamelModel):
    type: Literal["late-interaction"] = "late-interaction"
    model_id: str = Field(min_length=1)


class QueryExpansion(CamelModel):
    model_id: str = Field(min_length=1)


IndexSpec = Annotated[Bm25Index | VectorIndex, Field(discriminator="type")]
RerankerSpec = Annotated[
    CrossEncoderReranker | LateInteractionReranker, Field(discriminator="type")
]


class KbConfig(CamelModel):
    # chunking config
    chunking_method: ChunkingStrategy = "recursive"
    chunking_model_id: str | None = None
    max_chunk_size: int = Field(default=1024, gt=0)
    min_chunk_size: int = Field(default=256, gt=0)

    # indexing config
    index_types: list[IndexSpec] = Field(
        default_factory=lambda: [Bm25Index()], min_length=1
    )

    # retrieval config
    reranker: RerankerSpec | None = None
    query_expansion: QueryExpansion | None = None

    @model_validator(mode="after")
    def _child_smaller_than_parent(self) -> "KbConfig":
        if self.min_chunk_size >= self.max_chunk_size:
            raise ValueError("min_chunk_size must be smaller than parent_chunk_size")
        return self

    @model_validator(mode="after")
    def _semantic_needs_a_model(self) -> "KbConfig":
        if self.chunking_method == "semantic" and not self.chunking_model_id:
            raise ValueError("semantic chunking needs a chunking_model_id")
        return self