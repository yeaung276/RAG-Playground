from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.db.session import async_session_maker
from app.services.admin.priority_service import PriorityService
from app.services.chat.message_service import MessageService
from app.services.chat.session_service import SessionService
from app.services.agents.generation_service import GenerationService
from app.dependencies.services import (
    get_generation_service,
    get_message_service,
    get_priority_service,
    get_session_service,
)
from app.dependencies.session import require_session
from app.schemas.messages import (
    ChatResponse,
    DoneFrame,
    FeedbackRequest,
    TokenFrame,
    UserMessage,
)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/messages")
async def chat_send(
    request: UserMessage,
    session_id: str = Depends(require_session),
    generation: GenerationService = Depends(get_generation_service),
    sessions: SessionService = Depends(get_session_service),
):
    async with MessageService.from_session_maker(async_session_maker) as messages:
        await messages.create(session_id, request.sender, request.content)
    intercepted = await sessions.is_intercepted(session_id)

    async def stream():
        if intercepted:
            yield f"data: {DoneFrame().model_dump_json(by_alias=True)}\n\n"
            return

        reply = []
        async for frame in generation.stream_reply(request.content):
            if isinstance(frame, TokenFrame):
                reply.append(frame.delta)
            yield f"data: {frame.model_dump_json(by_alias=True)}\n\n"

        async with MessageService.from_session_maker(async_session_maker) as messages:
            message = await messages.create(session_id, generation.agent, "".join(reply))
        yield f"data: {DoneFrame(id=message.id).model_dump_json(by_alias=True)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/messages", response_model=list[ChatResponse])
async def get_messages(
    session_id: str = Depends(require_session),
    messages: MessageService = Depends(get_message_service),
):
    return await messages.list(session_id)


@router.post("/messages/{message_id}/feedback", response_model=ChatResponse)
async def set_message_feedback(
    message_id: str,
    request: FeedbackRequest,
    session_id: str = Depends(require_session),
    messages: MessageService = Depends(get_message_service),
    priority: PriorityService = Depends(get_priority_service),
):
    message = await messages.set_feedback(session_id, message_id, request.value)
    if request.value == "like":
        await priority.bump(session_id, upvote_delta=1)
    elif request.value == "dislike":
        await priority.bump(session_id, downvote_delta=1)
    return message
