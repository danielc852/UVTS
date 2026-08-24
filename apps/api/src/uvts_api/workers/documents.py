import asyncio

from redis.asyncio import Redis

from uvts_api.adapters.db.session import create_engine, create_session_factory
from uvts_api.adapters.notifications.redis import RedisStateNotifications
from uvts_api.adapters.storage.local import LocalDocumentStorage
from uvts_api.core.config import get_settings
from uvts_api.services.documents import process_pending_document
from uvts_api.workers.celery_app import celery_app


@celery_app.task(name="uvts.documents.process")  # type: ignore[untyped-decorator]
def process_document(document_id: str) -> None:
    asyncio.run(_process_document(document_id))


async def _process_document(document_id: str) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        async with session_factory() as db:
            await process_pending_document(
                db=db,
                storage=LocalDocumentStorage(settings.storage_root),
                notifications=RedisStateNotifications(
                    redis, heartbeat_seconds=settings.sse_heartbeat_seconds
                ),
                document_id=document_id,
            )
    finally:
        await redis.aclose()
        await engine.dispose()


def enqueue_document_processing(document_id: str) -> None:
    celery_app.send_task("uvts.documents.process", args=[document_id])
