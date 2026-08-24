import asyncio

from redis.asyncio import Redis

from uvts_api.adapters.db.session import create_engine, create_session_factory
from uvts_api.adapters.notifications.redis import RedisStateNotifications
from uvts_api.core.config import get_settings
from uvts_api.services.questions import (
    build_question_agent,
    fail_question_generation,
    process_question_generation,
)
from uvts_api.workers.celery_app import celery_app


@celery_app.task(name="uvts.questions.generate")  # type: ignore[untyped-decorator]
def generate_questions(test_id: str, operation_id: str) -> None:
    asyncio.run(_generate_questions(test_id, operation_id))


async def _generate_questions(test_id: str, operation_id: str) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    notifications = RedisStateNotifications(
        redis, heartbeat_seconds=settings.sse_heartbeat_seconds
    )
    try:
        async with session_factory() as db:
            try:
                agent = build_question_agent(settings)
            except Exception as error:
                await fail_question_generation(
                    db=db,
                    notifications=notifications,
                    test_id=test_id,
                    operation_id=operation_id,
                    error=error,
                )
                return
            await process_question_generation(
                db=db,
                notifications=notifications,
                agent=agent,
                test_id=test_id,
                operation_id=operation_id,
            )
    finally:
        await redis.aclose()
        await engine.dispose()


def enqueue_question_generation(test_id: str, operation_id: str) -> None:
    celery_app.send_task("uvts.questions.generate", args=[test_id, operation_id])
