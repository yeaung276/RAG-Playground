import asyncio
from collections.abc import AsyncIterator

import asyncpg
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.logger import get_logger

logger = get_logger("services.realtime")

QUEUE_MAXSIZE = 100

HEARTBEAT_INTERVAL = 3
HEARTBEAT_TIMEOUT = 2

CHAT_CHANNEL = "chat_events"
ADMIN_NOTI_CHANNEL = "admin_noti_channel"

# Event types.
MESSAGE_CREATED = "message.created"  # chat: a new message in a session
FEEDBACK_UPDATED = "feedback.updated"  # chat: a message's like/dislike changed
ADMIN_DIRTY = "admin.list.dirty"  # admin: the attention list changed -> refetch


class Event(BaseModel):
    """Domain payload. `topic` is transport routing and lives in the envelope, not
    here, so PubSub never inspects Event fields."""

    type: str
    session_id: str = ""
    data: dict = {}


class _Envelope(BaseModel):
    topic: str
    event: Event


def _listen_dsn() -> str:
    # asyncpg.connect wants a plain libpq DSN, not SQLAlchemy's "+asyncpg" URL.
    return get_settings().DATABASE_URL.replace("+asyncpg", "")


class PubSub:
    """Generic transport: owns the single per-pod asyncpg LISTEN connection and
    fans NOTIFYs out to in-process subscribers keyed by (channel, topic). Knows
    nothing about sessions or admins -- callers name their own channels/topics."""

    def __init__(self, channels: list[str]) -> None:
        self._channels = channels
        self._subs: dict[tuple[str, str], set[asyncio.Queue[Event]]] = {}
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass

    async def subscribe(self, channel: str, topic: str = "") -> AsyncIterator[Event]:
        """Yield events for (channel, topic) until the caller (an SSE stream) stops
        iterating or its connection drops."""
        key = (channel, topic)
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        self._subs.setdefault(key, set()).add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            subs = self._subs.get(key)
            if subs is not None:
                subs.discard(queue)
                if not subs:
                    del self._subs[key]

    def _dispatch(self, channel: str, payload: str) -> None:
        try:
            envelope = _Envelope.model_validate_json(payload)
        except Exception:
            logger.warning("dropping malformed pubsub payload: %r", payload[:200])
            return
        for queue in self._subs.get((channel, envelope.topic), set()):
            try:
                queue.put_nowait(envelope.event)
            except asyncio.QueueFull:
                logger.warning(
                    "dropping event for slow subscriber (channel: %s, topic: %s)",
                    channel,
                    envelope.topic,
                )

    async def _run(self) -> None:
        def handle(_conn, _pid, channel: str, payload: str) -> None:
            # Runs inline on the listen connection's callback: never block/await.
            self._dispatch(channel, payload)

        backoff = 1
        while True:
            conn: asyncpg.Connection | None = None
            try:
                conn = await asyncpg.connect(_listen_dsn())
                assert conn is not None
                for channel in self._channels:
                    await conn.add_listener(channel, handle)
                logger.info("pubsub listening on %s", self._channels)
                backoff = 1

                # Park until the connection dies; handle fires in the background
                # meanwhile. NOTIFYs missed during a reconnect gap are not
                # replayed (the client's refetch on reconnect covers it).
                terminated = asyncio.Event()
                conn.add_termination_listener(lambda _c: terminated.set())

                # A silently black-holed socket (idle eviction by a firewall/NAT,
                # no FIN/RST) never fires the termination listener, so we can't
                # just wait on it. Ping on an interval instead: a hung SELECT 1
                # surfaces the dead connection within HEARTBEAT_TIMEOUT and drops
                # us into reconnect. The ping doubles as keepalive -- it is real
                # traffic, so the flow never looks idle to a firewall.
                while not terminated.is_set():
                    try:
                        await asyncio.wait_for(terminated.wait(), HEARTBEAT_INTERVAL)
                    except asyncio.TimeoutError:
                        await asyncio.wait_for(conn.fetchval("SELECT 1"), HEARTBEAT_TIMEOUT)
                logger.warning("pubsub connection terminated; reconnecting")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("pubsub connect failed (%s); retry in %ss", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
            finally:
                # terminate(), not close(): a graceful close can hang on a dead
                # socket, and we discard the connection on every path regardless.
                if conn is not None and not conn.is_closed():
                    conn.terminate()


class Publisher:
    """Publishes events on the caller's DB session, inside the caller's
    transaction (pg_notify fires on COMMIT). The caller names the (channel, topic);
    Publisher stays domain-agnostic like PubSub."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def publish(self, channel: str, topic: str, event: Event) -> None:
        payload = _Envelope(topic=topic, event=event).model_dump_json()
        await self._db.execute(
            text("SELECT pg_notify(:channel, :payload)"),
            {"channel": channel, "payload": payload},
        )