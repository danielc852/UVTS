from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from uvts_api.adapters.db.session import create_engine, create_session_factory
from uvts_api.adapters.notifications.redis import RedisStateNotifications
from uvts_api.adapters.storage.local import LocalDocumentStorage
from uvts_api.core.config import Settings, get_settings


@dataclass(frozen=True)
class WorkerRuntime:
    """Resources shared by one background task invocation."""

    settings: Settings
    db: AsyncSession
    notifications: RedisStateNotifications
    storage: LocalDocumentStorage


@asynccontextmanager
async def open_worker_runtime() -> AsyncIterator[WorkerRuntime]:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)

    try:
        notifications = RedisStateNotifications(
            redis,
            heartbeat_seconds=settings.sse_heartbeat_seconds,
        )
        storage = LocalDocumentStorage(settings.storage_root)
        async with session_factory() as db:
            yield WorkerRuntime(
                settings=settings,
                db=db,
                notifications=notifications,
                storage=storage,
            )
    finally:
        await redis.aclose()
        await engine.dispose()
