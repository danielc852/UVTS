from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from uvts_api.adapters.db.models import TestRun
from uvts_api.api.dependencies import CurrentSession, DatabaseSession
from uvts_api.schemas.errors import ErrorResponse
from uvts_api.schemas.tests import TestCreateRequest, TestResponse
from uvts_api.services.events import stream_test_events
from uvts_api.services.tests import get_owned_test, to_test_response

router = APIRouter(prefix="/tests", tags=["tests"])


@router.post(
    "",
    response_model=TestResponse,
    status_code=201,
    responses={401: {"model": ErrorResponse}},
)
async def create_test(
    payload: TestCreateRequest,
    current: CurrentSession,
    db: DatabaseSession,
) -> TestResponse:
    test = TestRun(
        owner_session_id=current.id,
        state=payload.model_dump(mode="json", by_alias=True),
    )
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return to_test_response(test)


@router.get(
    "/{test_id}",
    response_model=TestResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_test(
    test_id: str,
    current: CurrentSession,
    db: DatabaseSession,
) -> TestResponse:
    return to_test_response(await get_owned_test(db, test_id, current.id))


@router.get(
    "/{test_id}/events",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "Persisted test-state events. Redis only signals clients to refetch.",
        },
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def test_events(
    test_id: str,
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
) -> StreamingResponse:
    # Authorize before sending streaming headers; each event refetch also enforces ownership.
    await get_owned_test(db, test_id, current.id)
    events = stream_test_events(
        test_id=test_id,
        owner_session_id=current.id,
        session_factory=request.app.state.session_factory,
        notifications=request.app.state.notifications,
    )
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
