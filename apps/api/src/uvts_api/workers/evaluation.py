import asyncio
from collections.abc import Sequence

from redis.asyncio import Redis

from uvts_api.adapters.ai.openrouter import build_openrouter_model
from uvts_api.adapters.db.models import TestRun
from uvts_api.adapters.db.session import create_engine, create_session_factory
from uvts_api.adapters.notifications.redis import RedisStateNotifications
from uvts_api.agents.evaluator import EvaluatorAgent
from uvts_api.core.config import Settings, get_settings
from uvts_api.services.evaluation import (
    fail_evaluation_dispatch,
    process_evaluation_operation,
)
from uvts_api.workers.celery_app import celery_app


@celery_app.task(name="uvts.evaluation.process")  # type: ignore[untyped-decorator]
def process_evaluation(test_id: str, operation_id: str, question_ids: list[str]) -> None:
    asyncio.run(_process_evaluation(test_id, operation_id, question_ids))


async def _process_evaluation(
    test_id: str,
    operation_id: str,
    question_ids: Sequence[str],
) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        async with session_factory() as db:
            test = await db.get(TestRun, test_id)
            operation_settings = _settings_for_operation(settings, test)
            notifications = RedisStateNotifications(
                redis, heartbeat_seconds=settings.sse_heartbeat_seconds
            )
            try:
                agent = EvaluatorAgent(
                    build_openrouter_model(operation_settings, temperature=0.0)
                )
            except Exception as error:
                await fail_evaluation_dispatch(
                    db=db,
                    notifications=notifications,
                    test_id=test_id,
                    operation_id=operation_id,
                    question_ids=question_ids,
                    error=error,
                )
                return
            await process_evaluation_operation(
                db=db,
                agent=agent,
                notifications=notifications,
                test_id=test_id,
                operation_id=operation_id,
                question_ids=question_ids,
            )
    finally:
        await redis.aclose()
        await engine.dispose()


def enqueue_evaluation_processing(
    test_id: str,
    operation_id: str,
    question_ids: Sequence[str],
) -> None:
    celery_app.send_task(
        "uvts.evaluation.process",
        args=[test_id, operation_id, list(question_ids)],
    )


def _settings_for_operation(settings: Settings, test: TestRun | None) -> Settings:
    if test is None:
        return settings
    evaluator_settings = test.agent_settings.get("evaluator")
    if not isinstance(evaluator_settings, dict):
        return settings
    model = evaluator_settings.get("model")
    timeout = evaluator_settings.get("requestTimeoutSeconds")
    updates: dict[str, object] = {}
    if isinstance(model, str) and model.strip():
        updates["openrouter_model"] = model
    if isinstance(timeout, int) and not isinstance(timeout, bool) and timeout > 0:
        updates["openrouter_request_timeout_seconds"] = timeout
    return settings.model_copy(update=updates)
