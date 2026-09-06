from typing import Literal

from app.schemas.base import CamelModel
from app.schemas.messages import ChatResponse, FeedbackEventData


class ChatFrame(CamelModel):
    """Base for the typed SSE frames on the chat channel. Building a frame from a
    raw event belongs to the Hydrator, not here."""


class MessageCreated(ChatFrame):
    """A message was persisted; `data` is the message itself."""

    type: Literal["message.created"] = "message.created"
    session_id: str
    data: ChatResponse


class FeedbackUpdated(ChatFrame):
    """A message's like/dislike changed; `data` is the message id and its new
    vote -- the message content itself is unchanged."""

    type: Literal["feedback.updated"] = "feedback.updated"
    session_id: str
    data: FeedbackEventData