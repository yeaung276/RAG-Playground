from app.schemas.base import CamelModel
from datetime import datetime

class LoginRequest(CamelModel):
    username: str
    password: str


class AdminRead(CamelModel):
    id: str
    username: str


class AdminMessage(CamelModel):
    content: str

class AdminChatSessionRead(CamelModel):
    id: str
    status: str
    created_at: datetime
    trigger_message: str | None = None
    priority: int = 0
    upvotes: int = 0
    downvotes: int = 0


class AdminChatSessionPage(CamelModel):
    items: list[AdminChatSessionRead]
    total: int
    page: int
    page_size: int