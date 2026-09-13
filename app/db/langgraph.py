from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.config import get_settings


def _checkpoint_dsn() -> str:
    # psycopg wants a plain libpq DSN, not SQLAlchemy's "+asyncpg" URL.
    return get_settings().DATABASE_URL.replace("+asyncpg", "")


class LGManager:
    """Owns the connection the checkpointer writes through and the graphs
    compiled against it. Built in the lifespan: the saver binds to the running
    loop, and the compiled graphs are meant to outlive a request."""

    def __init__(self) -> None:
        self._conn: AsyncConnection | None = None
        self._saver: AsyncPostgresSaver | None = None
        self._graphs: dict[tuple, CompiledStateGraph] = {}

    async def setup(self) -> None:
        self._conn = await AsyncConnection.connect(
            _checkpoint_dsn(), autocommit=True, prepare_threshold=0, row_factory=dict_row
        )
        self._saver = AsyncPostgresSaver(self._conn)
        await self._saver.setup()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            self._saver = None
        self._graphs.clear()

    async def get_or_create(
        self, key: dict[str, Any], loader: Callable[[], Awaitable[StateGraph]]
    ) -> CompiledStateGraph:
        """Read-through cache: on a miss `loader` builds the graph, which is
        compiled against the checkpointer and stored under `key`."""
        cache_key = tuple(sorted(key.items()))
        cached = self._graphs.get(cache_key)
        if cached is not None:
            return cached
        compiled = (await loader()).compile(checkpointer=self._saver)
        self._graphs[cache_key] = compiled
        return compiled
