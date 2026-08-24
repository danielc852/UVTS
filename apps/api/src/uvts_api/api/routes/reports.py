from fastapi import APIRouter, Request

from uvts_api.api.dependencies import CurrentSession, DatabaseSession, RuntimeSettings
from uvts_api.api.routes.evaluations import dispatch_evaluation
from uvts_api.schemas.errors import ErrorResponse
from uvts_api.schemas.tests import TestResponse
from uvts_api.services.evaluation import (
    publish_evaluation_change,
    start_report_retry,
)
from uvts_api.services.tests import get_owned_test, to_test_response

router = APIRouter(prefix="/tests", tags=["reports"])


@router.post(
    "/{test_id}/report/retry",
    response_model=TestResponse,
    status_code=202,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def retry_report(
    test_id: str,
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id)
    operation_id, question_ids = await start_report_retry(db=db, test=test)
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
