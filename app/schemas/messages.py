from datetime import datetime
from typing import Any, Literal

from app.schemas.base import CamelModel


Feedback = Literal["like", "dislike"]


class UserMessage(CamelModel):
    sender: str
    content: str | None = None


class FeedbackRequest(CamelModel):
    # null clears the vote (unvote); "like"/"dislike" set or switch it.
    value: Feedback | None = None


class FeedbackEventData(CamelModel):
    # Payload of a feedback.updated event: the message id and its new vote.
    id: str
    feedback: Feedback | None = None


class TokenFrame(CamelModel):
    type: Literal["token"] = "token"
    agent: str | None = None
    delta: str

    
class ThinkingFrame(CamelModel):
    type: Literal["thinking"] = "thinking"
    agent: str | None = None
    delta: str


class ToolCallFrame(CamelModel):
    type: Literal["tool_call"] = "tool_call"
    name: str


class ToolResultFrame(CamelModel):
    type: Literal["tool_result"] = "tool_result"
    agent: str | None = None
    name: str | None = None
    args: dict[str, Any] = {}
    content: str = ""
    status: Literal["success", "error"] = "success"
    elapsed_ms: int | None = None


class MessageFrame(CamelModel):
    type: Literal["message"] = "message"
    agent: str | None = None
    role: Literal["human", "ai"]
    content: str = ""
    thinking: str | None = None
    usage: dict[str, Any] | None = None


class DoneFrame(CamelModel):
    type: Literal["done"] = "done"
    id: str | None = None


class ErrorFrame(CamelModel):
    type: Literal["error"] = "error"
    message: str


class ChatResponse(CamelModel):
    id: str
    session_id: str
    sender: str
    content: str | None
    created_at: datetime
    feedback: Feedback | None = None
