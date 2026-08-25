import asyncio
from collections.abc import Sequence

from uvts_api.adapters.ai.openrouter import build_openrouter_model
from uvts_api.adapters.db.models import TestRun
from uvts_api.agents.evaluator import EvaluatorAgent
from uvts_api.services.evaluation import (
    fail_evaluation_dispatch,
    process_evaluation_operation,
)
from uvts_api.workers.celery_app import celery_app
from uvts_api.workers.runtime import open_worker_runtime
from uvts_api.workers.settings import settings_for_agent


@celery_app.task(name="uvts.evaluation.process")  # type: ignore[untyped-decorator]
def process_evaluation(test_id: str, operation_id: str, question_ids: list[str]) -> None:
    asyncio.run(_process_evaluation(test_id, operation_id, question_ids))


async def _process_evaluation(
    test_id: str,
    operation_id: str,
    question_ids: Sequence[str],
) -> None:
    async with open_worker_runtime() as runtime:
        test = await runtime.db.get(TestRun, test_id)
        operation_settings = settings_for_agent(
            runtime.settings,
            test.agent_settings if test is not None else None,
            agent="evaluator",
        )
        try:
            agent = EvaluatorAgent(
                build_openrouter_model(operation_settings, temperature=0.0)
            )
        except Exception as error:
            await fail_evaluation_dispatch(
                db=runtime.db,
                notifications=runtime.notifications,
                test_id=test_id,
                operation_id=operation_id,
                question_ids=question_ids,
                error=error,
            )
            return
        await process_evaluation_operation(
            db=runtime.db,
            storage=runtime.storage,
            agent=agent,
            notifications=runtime.notifications,
            test_id=test_id,
            operation_id=operation_id,
            question_ids=question_ids,
        )


def enqueue_evaluation_processing(
    test_id: str,
    operation_id: str,
    question_ids: Sequence[str],
) -> None:
    celery_app.send_task(
        "uvts.evaluation.process",
        args=[test_id, operation_id, list(question_ids)],
    )
