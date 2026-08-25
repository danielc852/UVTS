import asyncio

from uvts_api.adapters.db.models import TestRun
from uvts_api.services.questions import (
    build_question_agent,
    fail_question_generation,
    process_question_generation,
)
from uvts_api.workers.celery_app import celery_app
from uvts_api.workers.runtime import open_worker_runtime
from uvts_api.workers.settings import settings_for_agent


@celery_app.task(name="uvts.questions.generate")  # type: ignore[untyped-decorator]
def generate_questions(test_id: str, operation_id: str) -> None:
    asyncio.run(_generate_questions(test_id, operation_id))


async def _generate_questions(test_id: str, operation_id: str) -> None:
    async with open_worker_runtime() as runtime:
        try:
            test = await runtime.db.get(TestRun, test_id)
            operation_settings = settings_for_agent(
                runtime.settings,
                test.agent_settings if test is not None else None,
                agent="questionAgent",
            )
            agent = build_question_agent(operation_settings)
        except Exception as error:
            await fail_question_generation(
                db=runtime.db,
                notifications=runtime.notifications,
                test_id=test_id,
                operation_id=operation_id,
                error=error,
            )
            return
        await process_question_generation(
            db=runtime.db,
            storage=runtime.storage,
            notifications=runtime.notifications,
            agent=agent,
            test_id=test_id,
            operation_id=operation_id,
        )


def enqueue_question_generation(test_id: str, operation_id: str) -> None:
    celery_app.send_task("uvts.questions.generate", args=[test_id, operation_id])
