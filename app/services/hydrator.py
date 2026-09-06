from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.logger import get_logger
from app.schemas.events import ChatFrame, FeedbackUpdated, MessageCreated
from app.schemas.messages import ChatResponse
from app.services.chat.message_service import MessageService
from app.services.realtime import FEEDBACK_UPDATED, MESSAGE_CREATED, Event

logger = get_logger("services.hydrator")


class Hydrator:
    """Turns a raw channel Event into the typed SSE frame a stream sends."""

    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._sessionmaker = session_maker

    async def hydrate(self, event: Event) -> ChatFrame | None:
        """None means drop the event: its row is gone, or the type is unknown."""
        handler = self._HANDLERS.get(event.type)
        if handler is None:
            logger.warning("dropping event of unknown type: %s", event.type)
            return None
        return await handler(self, event)

    async def _message_created(self, event: Event) -> ChatFrame | None:
        async with MessageService.from_session_maker(self._sessionmaker) as messages:
            message = await messages.get(event.session_id, event.data["id"])
            if message is None:
                logger.warning("dropping event for missing message: %s", event.data)
                return None
            return MessageCreated(
                session_id=event.session_id,
                data=ChatResponse.model_validate(message),
            )

    async def _feedback_updated(self, event: Event) -> ChatFrame | None:
        return FeedbackUpdated.model_validate(event)


    _HANDLERS: dict[str, Callable[["Hydrator", Event], Awaitable[ChatFrame | None]]] = {
        MESSAGE_CREATED: _message_created,
        FEEDBACK_UPDATED: _feedback_updated,
    }
