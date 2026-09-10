from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.schemas.base import CamelModel


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
    """`auth_token` omitted keeps the stored one; `auth: none` erases it."""

    auth_token: str | None = None


class ToolRead(ToolBase):
    has_auth_token: bool = False


class ToolTestRequest(CamelModel):
    """Try a tool as currently edited. `tool.auth_token` omitted falls back to
    the token already stored for that tool name."""

    tool: ToolWrite
    params: dict[str, str] = Field(default_factory=dict)


class SentRequest(CamelModel):
    method: str
    url: str
    headers: dict[str, str]
    query: dict[str, str]
    body: str | None


class ToolTestResult(CamelModel):
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


class AgentCreate(CamelModel):
    name: str
    description: str = ""
    instruction: str = ""
    model_id: str | None = None
    temperature: int = Field(default=0, ge=0, le=100)
    knowledge_id: str | None = None
    max_step: int = Field(default=10, ge=1)
    tools: list[ToolWrite] = Field(default_factory=list)
    handoff: Handoff = Field(default_factory=Handoff)


class AgentUpdate(CamelModel):
    """`tools` is the whole list: names not sent are deleted. The agent's own
    `name` is fixed at creation and cannot be patched."""

    description: str | None = None
    instruction: str | None = None
    model_id: str | None = None
    temperature: int | None = Field(default=None, ge=0, le=100)
    knowledge_id: str | None = None
    max_step: int | None = Field(default=None, ge=1)
    tools: list[ToolWrite] | None = None
    handoff: Handoff | None = None


class AgentSummary(CamelModel):
    """Roster row. Tools and handoff targets are counted here rather than
    inlined — the full documents come from the detail endpoint."""

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
    max_step: int
    tools: list[ToolRead]
    handoff: Handoff
    is_entrypoint: bool
    created_at: datetime
    updated_at: datetime
