from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from app.schemas.base import CamelModel


class Capability(StrEnum):
    BI_ENCODER = "bi-encoder"      # embeddings
    CROSS_ENCODER = "cross-encoder"  # reranking
    DECODER = "decoder"            # chat / generation


class ApiSchema(StrEnum):
    OPENAI = "openai"  # /embeddings, /chat/completions
    TEI = "tei"        # /embed, /rerank
    COHERE = "cohere"  # /rerank, Cohere-style body
    GEMINI = "gemini"  # /interactions, Gemini-native body


VALID_PAIRS: dict[ApiSchema, set[Capability]] = {
    ApiSchema.OPENAI: {Capability.BI_ENCODER, Capability.DECODER},
    ApiSchema.TEI: {Capability.BI_ENCODER, Capability.CROSS_ENCODER},
    ApiSchema.COHERE: {Capability.CROSS_ENCODER},
    ApiSchema.GEMINI: {Capability.BI_ENCODER, Capability.DECODER},
}


class ModelCreate(CamelModel):
    provider: str
    api_schema: ApiSchema = Field(alias="schema")
    base_url: str
    api_key: str | None = None
    name: str
    capability: Capability

    @model_validator(mode="after")
    def check_pair(self):
        if self.capability not in VALID_PAIRS[self.api_schema]:
            raise ValueError(f"{self.api_schema} does not serve {self.capability} models")
        return self


class ModelUpdate(CamelModel):
    provider: str | None = None
    base_url: str | None = None
    api_key: str | None = None 
    name: str | None = None


class ModelRead(CamelModel):
    id: str
    provider: str
    api_schema: ApiSchema = Field(alias="schema")
    base_url: str
    has_api_key: bool
    name: str
    capability: Capability
    created_at: datetime


class ModelPage(CamelModel):
    items: list[ModelRead]
    total: int
    page: int
    page_size: int
