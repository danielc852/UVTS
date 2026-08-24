from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from uvts_api.adapters.db.base import Base
from uvts_api.adapters.db.session import create_engine, create_session_factory
from uvts_api.adapters.notifications.redis import RedisStateNotifications
from uvts_api.adapters.storage.local import LocalDocumentStorage
from uvts_api.api.router import api_router
from uvts_api.core.config import Settings, get_settings
from uvts_api.core.http import RequestIdMiddleware, install_error_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(runtime_settings.database_url)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.redis = Redis.from_url(runtime_settings.redis_url, decode_responses=True)
        app.state.notifications = RedisStateNotifications(
            app.state.redis,
            heartbeat_seconds=runtime_settings.sse_heartbeat_seconds,
        )
        app.state.document_storage = LocalDocumentStorage(runtime_settings.storage_root)
        if runtime_settings.auto_create_schema:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        try:
            yield
        finally:
            await app.state.redis.aclose()
            await engine.dispose()

    app = FastAPI(
        title=runtime_settings.app_name,
        version="0.1.0",
        description="Private API for the UVTS document-testing workspace.",
        lifespan=lifespan,
    )
    app.state.settings = runtime_settings
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Accept-Ranges", "Content-Length", "Content-Range", "ETag"],
    )
    install_error_handlers(app)
    app.include_router(api_router, prefix=runtime_settings.api_v1_prefix)
    return app


app = create_app()
