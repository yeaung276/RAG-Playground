from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.agent_service import AgentService
from app.services.agents.generation_service import GenerationService
from app.services.chat.session_service import SessionService
from app.services.chat.message_service import MessageService
from app.services.realtime import Publisher, PubSub
from app.services.hydrator import Hydrator
from app.services.knowledge.file_service import FileService
from app.services.knowledge.kb_service import KnowledgeBaseService
from app.services.admin.admin_service import AdminService
from app.services.model_service import ModelService
from app.services.admin.admin_session_service import AdminSessionService
from app.services.admin.priority_service import PriorityService
from app.backgrounds.files_processor import FileProcessor
from app.db.qdrant import qdrant
from app.db.langgraph import LGManager
from app.db.session import async_session_maker
from app.dependencies.database import get_session
from app.services.retrieval.extraction_service import ExtractionService
from app.services.retrieval.indexing_service import IndexingService
from app.storage import get_storage
from app.config import get_settings

def get_pubsub(request: Request) -> PubSub:
    return request.app.state.pubsub


def get_langgraph(request: Request) -> LGManager:
    return request.app.state.langgraph


def get_generation_service(
    langgraph: LGManager = Depends(get_langgraph),
) -> GenerationService:
    return GenerationService(async_session_maker, langgraph)


def get_session_service(
    pubsub: PubSub = Depends(get_pubsub),
) -> SessionService:
    return SessionService(async_session_maker, pubsub)


def get_hydrator() -> Hydrator:
    return Hydrator(async_session_maker)


def get_publisher(db: AsyncSession = Depends(get_session)) -> Publisher:
    return Publisher(db)


def get_message_service(
    db: AsyncSession = Depends(get_session),
    publisher: Publisher = Depends(get_publisher),
) -> MessageService:
    return MessageService(db, publisher)


def get_kb_service(
    session: AsyncSession = Depends(get_session),
) -> KnowledgeBaseService:
    return KnowledgeBaseService(session=session, qdrant=qdrant)


def get_model_service(session: AsyncSession = Depends(get_session)) -> ModelService:
    return ModelService(session)


def get_agent_service(session: AsyncSession = Depends(get_session)) -> AgentService:
    return AgentService(session)


def get_admin_service(session: AsyncSession = Depends(get_session)) -> AdminService:
    return AdminService(session)


def get_admin_session_service(
    session: AsyncSession = Depends(get_session),
) -> AdminSessionService:
    return AdminSessionService(session)


def get_priority_service(
    session: AsyncSession = Depends(get_session),
    publisher: Publisher = Depends(get_publisher),
) -> PriorityService:
    return PriorityService(session, publisher)


def get_file_service(
    session: AsyncSession = Depends(get_session),
) -> FileService:
    storage = get_storage()
    return FileService(session=session, storage=storage)


def get_extraction_service() -> ExtractionService:
    return ExtractionService()


def get_file_processor() -> FileProcessor:
    return FileProcessor(
        get_storage(),
        get_extraction_service(),
        IndexingService(async_session_maker, qdrant),
        async_session_maker,
    )
