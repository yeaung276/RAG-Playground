from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies.services import get_pubsub
from app.services.realtime import ADMIN_NOTI_CHANNEL, PubSub

router = APIRouter(prefix="/notifications", tags=["admin-notifications"])


@router.get("")
async def notifications(pubsub: PubSub = Depends(get_pubsub)):
    """Admin realtime notification stream, opened once on page load. General
    purpose; currently carries admin.list.dirty (attention list changed ->
    refetch). Broadcast: every admin on this pod gets every event."""

    async def stream():
        yield ": connected\n\n"
        async for event in pubsub.subscribe(ADMIN_NOTI_CHANNEL):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
