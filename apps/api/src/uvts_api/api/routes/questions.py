from fastapi import APIRouter, Request

from uvts_api.api.dependencies import (
    CurrentSession,
    DatabaseSession,
    DocumentStorageDependency,
    OperationDispatcherDependency,
    RuntimeSettings,
)
from uvts_api.schemas.errors import ErrorResponse
from uvts_api.schemas.questions import ConfirmQuestionsRequest
from uvts_api.schemas.tests import TestResponse
from uvts_api.services.questions import (
    begin_question_generation,
    confirm_questions,
    publish_question_change,
    start_over,
)
from uvts_api.services.tests import get_owned_test, to_test_response

router = APIRouter(prefix="/tests", tags=["questions"])


@router.post(
    "/{test_id}/questions",
    response_model=TestResponse,
    status_code=202,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def generate_test_questions(
    test_id: str,
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
    settings: RuntimeSettings,
    operation_dispatcher: OperationDispatcherDependency,
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id)
    operation = await begin_question_generation(
        db=db,
        notifications=request.app.state.notifications,
        test=test,
        settings=settings,
    )
    await operation_dispatcher.generate_questions(
        test_id=operation.test_id,
        operation_id=operation.operation_id,
    )
    await db.refresh(test)
    return await to_test_response(db, test)


@router.post(
    "/{test_id}/questions/confirm",
    response_model=TestResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def confirm_test_questions(
    test_id: str,
    request: Request,
    payload: ConfirmQuestionsRequest,
    current: CurrentSession,
    db: DatabaseSession,
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id)
    await confirm_questions(db=db, test=test, items=payload.items)
    await publish_question_change(request.app.state.notifications, test.id)
    await db.refresh(test)
    return await to_test_response(db, test)


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
    return await to_test_response(db, test)
