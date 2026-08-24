from fastapi import APIRouter, Request

from uvts_api.api.dependencies import (
    CurrentSession,
    DatabaseSession,
    DocumentStorageDependency,
    RuntimeSettings,
)
from uvts_api.schemas.errors import ErrorResponse
from uvts_api.schemas.tests import TestResponse
from uvts_api.services.questions import (
    begin_question_generation,
    build_question_agent,
    confirm_questions,
    fail_question_generation,
    process_question_generation,
    publish_question_change,
    start_over,
)
from uvts_api.services.tests import get_owned_test, to_test_response
from uvts_api.workers.questions import enqueue_question_generation

router = APIRouter(prefix="/tests", tags=["questions"])


async def dispatch_question_generation(
    *,
    request: Request,
    db: DatabaseSession,
    storage: DocumentStorageDependency,
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
        storage=storage,
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
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
    storage: DocumentStorageDependency,
    settings: RuntimeSettings,
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id)
    operation = await begin_question_generation(
        db=db,
        notifications=request.app.state.notifications,
        test=test,
        settings=settings,
    )
    await dispatch_question_generation(
        request=request,
        db=db,
        storage=storage,
        settings=settings,
        test_id=operation.test_id,
        operation_id=operation.operation_id,
    )
    await db.refresh(test)
    return to_test_response(test)


@router.post(
    "/{test_id}/questions/confirm",
    response_model=TestResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def confirm_test_questions(
    test_id: str,
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id)
    await confirm_questions(db=db, test=test)
    await publish_question_change(request.app.state.notifications, test.id)
    await db.refresh(test)
    return to_test_response(test)


@router.post(
    "/{test_id}/start-over",
    response_model=TestResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def start_test_over(
    test_id: str,
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
    storage: DocumentStorageDependency,
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id)
    await start_over(db=db, storage=storage, test=test)
    await publish_question_change(request.app.state.notifications, test.id)
    await db.refresh(test)
    return to_test_response(test)
