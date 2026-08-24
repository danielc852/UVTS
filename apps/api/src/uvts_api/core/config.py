from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded only on the server."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "UVTS API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(
        default="postgresql+asyncpg://uvts:uvts@localhost:5432/uvts",
        validation_alias=AliasChoices("DATABASE_URL", "UVTS_DATABASE_URL"),
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("REDIS_URL", "UVTS_REDIS_URL"),
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        validation_alias=AliasChoices("ALLOWED_ORIGINS", "UVTS_CORS_ORIGINS"),
    )
    session_cookie_name: str = "uvts_session"
    session_cookie_secure: bool = Field(
        default=False,
        validation_alias=AliasChoices("SESSION_COOKIE_SECURE", "UVTS_SESSION_COOKIE_SECURE"),
    )
    session_secret: SecretStr | None = Field(default=None, validation_alias="SESSION_SECRET")
    session_ttl_seconds: int = 60 * 60 * 24 * 7
    storage_root: Path = Field(
        default=Path(".data/documents"),
        validation_alias=AliasChoices("PRIVATE_STORAGE_PATH", "UVTS_STORAGE_ROOT"),
    )
    document_processing_eager: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "DOCUMENT_PROCESSING_EAGER", "UVTS_DOCUMENT_PROCESSING_EAGER"
        ),
    )
    agent_processing_eager: bool = Field(
        default=False,
        validation_alias=AliasChoices("AGENT_PROCESSING_EAGER", "UVTS_AGENT_PROCESSING_EAGER"),
    )
    openrouter_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "UVTS_OPENROUTER_API_KEY"),
    )
    openrouter_model: str = Field(
        default="qwen/qwen3.8-27b",
        validation_alias=AliasChoices("OPENROUTER_MODEL", "UVTS_OPENROUTER_MODEL"),
    )
    openrouter_request_timeout_seconds: int = Field(
        default=60,
        gt=0,
        validation_alias=AliasChoices(
            "OPENROUTER_REQUEST_TIMEOUT_SECONDS",
            "UVTS_OPENROUTER_REQUEST_TIMEOUT_SECONDS",
        ),
    )
    agent_max_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
        validation_alias=AliasChoices("AGENT_MAX_ATTEMPTS", "UVTS_AGENT_MAX_ATTEMPTS"),
    )
    sse_heartbeat_seconds: float = 15.0
    auto_create_schema: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
