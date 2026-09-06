from datetime import datetime
from typing import Literal

from app.schemas.base import CamelModel


Feedback = Literal["like", "dislike"]


class UserMessage(CamelModel):
    sender: str
    content: str | None = None
    image_base64: str | None = None
    image_mime_type: str | None = None


class FeedbackRequest(CamelModel):
    # null clears the vote (unvote); "like"/"dislike" set or switch it.
    value: Feedback | None = None


class FeedbackEventData(CamelModel):
    # Payload of a feedback.updated event: the message id and its new vote.
    id: str
    feedback: Feedback | None = None


class TokenFrame(CamelModel):
    type: Literal["token"] = "token"
    delta: str


class ToolCallFrame(CamelModel):
    type: Literal["tool_call"] = "tool_call"
    name: str


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
    has_image: bool
    created_at: datetime
    feedback: Feedback | None = None
