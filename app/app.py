from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import router, static
from app.db.qdrant import qdrant
from app.db.session import async_session_maker, engine
from app.middlewares.security import SecurityHeadersMiddleware
from app.services.realtime import ADMIN_NOTI_CHANNEL, CHAT_CHANNEL, PubSub
from app.metrics import instrumentator
from app.logger import get_logger
from app.config import get_settings


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    app.state.pubsub = PubSub([CHAT_CHANNEL, ADMIN_NOTI_CHANNEL])
    await app.state.pubsub.start()
    yield
    await app.state.pubsub.stop()
    await engine.dispose()
    await qdrant.close()
    logger.info("Application shutting down...")


app = FastAPI(lifespan=lifespan)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Routes
app.include_router(router.router)

# Prometheus metrics: default HTTP metrics + custom metrics, exposed at /metrics
instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# Files
app.mount("/", app=static.static, name="static")



