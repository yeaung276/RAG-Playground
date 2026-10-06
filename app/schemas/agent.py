from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, model_validator

from app.schemas.base import CamelModel
from app.services.retrieval.document import IndexSpec


class HandoffMode(StrEnum):
    NONE = "none"      # answers everything itself
    AUTO = "auto"      # every other agent is a target
    MANUAL = "manual"  # only the listed targets


class AuthKind(StrEnum):
    NONE = "none"
    BEARER = "bearer"
    HEADER = "header"
    BASIC = "basic"


class KV(CamelModel):
    id: str | None = None
    key: str
    value: str


class Param(CamelModel):
    id: str | None = None
    name: str
    type: str
    required: bool = False
    description: str = ""


class ToolBase(CamelModel):
    id: str | None = None
    name: str
    description: str = ""
    enabled: bool = True
    method: str = "GET"
    url: str = ""
    headers: list[KV] = Field(default_factory=list)
    query: list[KV] = Field(default_factory=list)
    body: str = ""
    auth: AuthKind = AuthKind.NONE
    auth_header: str = ""
    auth_user: str = ""
    auth_pass: str = ""
    timeout_ms: int = 30000
    params: list[Param] = Field(default_factory=list)


class ToolWrite(ToolBase):
    auth_token: str | None = None


class ToolRead(ToolBase):
    has_auth_token: bool = False


class AgentTestRequest(CamelModel):
    thread_id: str
    message: str


class ToolTestRequest(CamelModel):
    tool: ToolWrite
    params: dict[str, str] = Field(default_factory=dict)


class SentRequest(CamelModel):
    method: str
    url: str
    headers: dict[str, str]
    query: dict[str, str]
    body: str | None


class ToolTestResult(CamelModel):
    args: dict[str, Any] = {}
    request: SentRequest
    status: int | None
    elapsed_ms: int
    body: str
    error: str | None


class HandoffTarget(CamelModel):
    id: str | None = None
    agent_id: str
    description: str = ""


class Handoff(CamelModel):
    mode: HandoffMode = HandoffMode.NONE
    targets: list[HandoffTarget] = Field(default_factory=list)


class KnowledgeConfig(CamelModel):
    index_types: list[IndexSpec] = Field(min_length=1)
    top_k: int | None = Field(default=None, gt=0)
    rerank_on: Literal["parent", "child"] | None = None
    rerank_pool: int | None = Field(default=None, gt=0)
    prefetch_limit: int | None = Field(default=None, gt=0)


class AgentCreate(CamelModel):
    name: str


class AgentUpdate(CamelModel):
    description: str | None = None
    instruction: str | None = None
    model_id: str | None = None
    temperature: int | None = Field(default=None, ge=0, le=100)
    knowledge_id: str | None = None
    knowledge_config: KnowledgeConfig | None = None
    max_step: int | None = Field(default=None, ge=1)
    tools: list[ToolWrite] | None = None
    handoff: Handoff | None = None

    @model_validator(mode="after")
    def _knowledge_needs_a_config(self) -> "AgentUpdate":
        if self.knowledge_id is not None and self.knowledge_config is None:
            raise ValueError("knowledge_config is required when knowledge_id is set")
        return self


class AgentSummary(CamelModel):
    id: str
    name: str
    description: str
    is_entrypoint: bool
    handoff_mode: HandoffMode
    enabled_tool_count: int
    handoff_count: int
    created_at: datetime
    updated_at: datetime


class AgentRead(CamelModel):
    id: str
    name: str
    description: str
    instruction: str
    model_id: str | None
    temperature: int
    knowledge_id: str | None
    knowledge_config: KnowledgeConfig | None
    max_step: int
    tools: list[ToolRead]
    handoff: Handoff
    is_entrypoint: bool
    created_at: datetime
    updated_at: datetime
