from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    ENV: str = Field(default="DEV")
    LOG_LEVEL: str = Field(default="info")
    AGENT_NAME: str = Field(default="Assistant")

    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1")
    OPENAI_API_KEY: str = Field(default="")
    GENERATION_MODEL: str = Field(default="gpt-4o-mini")

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/chat_gateway"
    )
    DB_ECHO: bool = Field(default=False)

    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_API_KEY: str | None = Field(default=None)

    ALLOWED_ORIGINS: str = Field(default="http://localhost:5173")
    SESSION_COOKIE_NAME: str = Field(default="chat_session")
    SESSION_COOKIE_SECURE: bool = Field(default=True)
    SESSION_COOKIE_SAMESITE: str = Field(default="none")
    SESSION_TIMEOUT_MINUTES: int = Field(default=30)

    # Admin console auth: signed-cookie session (no server-side store).
    ADMIN_SECRET_KEY: str = Field(default="change-me-in-production")
    ADMIN_COOKIE_NAME: str = Field(default="admin_session")
    ADMIN_SESSION_HOURS: int = Field(default=1)
    
    STORAGE_PATH: str = Field(default=".knowledge/storage")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache()
def get_settings():
    return Settings()
