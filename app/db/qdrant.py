from qdrant_client import AsyncQdrantClient

from app.config import get_settings

settings = get_settings()

qdrant = AsyncQdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY,
)