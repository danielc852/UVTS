from collections.abc import Sequence
from typing import Any, cast

from fastapi import APIRouter, Request
from langchain_core.language_models.chat_models import BaseChatModel

from uvts_api.adapters.ai.openrouter import build_openrouter_model
from uvts_api.agents.evaluator import EvaluatorAgent
from uvts_api.api.dependencies import CurrentSession, DatabaseSession, RuntimeSettings
from uvts_api.core.config import Settings
from uvts_api.schemas.errors import ErrorResponse
from uvts_api.schemas.tests import TestResponse
from uvts_api.services.evaluation import (
    fail_evaluation_dispatch,
    process_evaluation_operation,
    publish_evaluation_change,
    start_evaluation,
    start_failed_retries,
    start_question_retry,
)
from uvts_api.services.tests import get_owned_test, to_test_response
from uvts_api.workers.evaluation import enqueue_evaluation_processing

router = APIRouter(prefix="/tests", tags=["evaluation"])

_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}


@router.post(
    "/{test_id}/evaluation",
    response_model=TestResponse,
    status_code=202,
    responses=_ERROR_RESPONSES,
)
async def evaluate_questions(
    test_id: str,
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id)
    operation_id, question_ids = await start_evaluation(
        db=db,
        test=test,
        agent_settings=_recorded_agent_settings(settings),
    )
    await publish_evaluation_change(request.app.state.notifications, test_id)
    await dispatch_evaluation(
        request=request,
        db=db,
        settings=settings,
        test_id=test_id,
        operation_id=operation_id,
        question_ids=question_ids,
    )
    await db.refresh(test)
    return to_test_response(test)


@router.post(
    "/{test_id}/evaluation/{question_id}/retry",
    response_model=TestResponse,
    status_code=202,
    responses=_ERROR_RESPONSES,
)
async def retry_question(
    test_id: str,
    question_id: str,
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id)
    operation_id, question_ids = await start_question_retry(
        db=db,
        test=test,
        question_id=question_id,
    )
    await publish_evaluation_change(request.app.state.notifications, test_id)
    await dispatch_evaluation(
        request=request,
        db=db,
        settings=settings,
        test_id=test_id,
        operation_id=operation_id,
        question_ids=question_ids,
    )
    await db.refresh(test)
    return to_test_response(test)


@router.post(
    "/{test_id}/evaluation/retry-failed",
    response_model=TestResponse,
    status_code=202,
    responses=_ERROR_RESPONSES,
)
async def retry_failed_questions(
    test_id: str,
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id)
    operation_id, question_ids = await start_failed_retries(db=db, test=test)
    await publish_evaluation_change(request.app.state.notifications, test_id)
    await dispatch_evaluation(
        request=request,
        db=db,
        settings=settings,
        test_id=test_id,
        operation_id=operation_id,
        question_ids=question_ids,
    )
    await db.refresh(test)
    return to_test_response(test)


async def dispatch_evaluation(
    *,
    request: Request,
    db: DatabaseSession,
    settings: Settings,
    test_id: str,
    operation_id: str,
    question_ids: Sequence[str],
) -> None:
    if settings.agent_processing_eager:
        try:
            agent = _request_evaluator(request, settings)
        except Exception as error:
            await fail_evaluation_dispatch(
                db=db,
                notifications=request.app.state.notifications,
                test_id=test_id,
                operation_id=operation_id,
                question_ids=question_ids,
                error=error,
            )
            return
        await process_evaluation_operation(
            db=db,
            agent=agent,
            notifications=request.app.state.notifications,
            test_id=test_id,
            operation_id=operation_id,
            question_ids=question_ids,
        )
    else:
        try:
            enqueue_evaluation_processing(test_id, operation_id, question_ids)
        except Exception as error:
            await fail_evaluation_dispatch(
                db=db,
                notifications=request.app.state.notifications,
                test_id=test_id,
                operation_id=operation_id,
                question_ids=question_ids,
                error=error,
            )


def _request_evaluator(request: Request, settings: Settings) -> EvaluatorAgent:
    configured = getattr(request.app.state, "chat_model", None)
    if configured is not None:
        return EvaluatorAgent(cast(BaseChatModel, configured))
    return EvaluatorAgent(build_openrouter_model(settings, temperature=0.0))


def _recorded_agent_settings(settings: Settings) -> dict[str, object]:
    return {
        "provider": "openrouter",
        "model": settings.openrouter_model,
        "temperature": 0.0,
        "requestTimeoutSeconds": settings.openrouter_request_timeout_seconds,
        "maxRetries": 2,
    }
