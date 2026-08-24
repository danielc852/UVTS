from fastapi import APIRouter, Request

from uvts_api.api.dependencies import (
    CurrentSession,
    DatabaseSession,
    RuntimeSettings,
)
from uvts_api.schemas.errors import ErrorResponse
from uvts_api.schemas.tests import TestResponse
from uvts_api.schemas.workspace import TestConfiguration
from uvts_api.services.questions import (
    begin_question_generation,
    build_question_agent,
    fail_question_generation,
    process_question_generation,
)
from uvts_api.services.tests import get_owned_test, to_test_response
from uvts_api.workers.questions import enqueue_question_generation

router = APIRouter(prefix="/tests", tags=["questions"])


async def dispatch_question_generation(
    *,
    request: Request,
    db: DatabaseSession,
    settings: RuntimeSettings,
    test_id: str,
    operation_id: str,
) -> None:
    if not settings.agent_processing_eager:
        try:
            enqueue_question_generation(test_id, operation_id)
        except Exception as error:
            await fail_question_generation(
                db=db,
                notifications=request.app.state.notifications,
                test_id=test_id,
                operation_id=operation_id,
                error=error,
            )
        return

    try:
        agent = build_question_agent(settings)
    except Exception as error:
        await fail_question_generation(
            db=db,
            notifications=request.app.state.notifications,
            test_id=test_id,
            operation_id=operation_id,
            error=error,
        )
        return
    await process_question_generation(
        db=db,
        notifications=request.app.state.notifications,
        agent=agent,
        test_id=test_id,
        operation_id=operation_id,
    )


@router.post(
    "/{test_id}/questions",
    response_model=TestResponse,
    status_code=202,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def generate_test_questions(
    test_id: str,
    payload: TestConfiguration,
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id)
    operation = await begin_question_generation(
        db=db,
        notifications=request.app.state.notifications,
        test=test,
        configuration=payload,
        settings=settings,
    )
    await dispatch_question_generation(
        request=request,
        db=db,
        settings=settings,
        test_id=operation.test_id,
        operation_id=operation.operation_id,
    )
    await db.refresh(test)
    return to_test_response(test)
