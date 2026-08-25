from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from uvts_api.adapters.db.models import TestRun
from uvts_api.core.errors import AppError, test_not_found
from uvts_api.schemas.tests import TestResponse
from uvts_api.schemas.workspace import WorkspaceState


def to_test_response(test: TestRun) -> TestResponse:
    try:
        state = WorkspaceState.model_validate(test.state)
    except ValidationError as exc:
        raise AppError(
            status_code=409,
            code="workspace_state_incompatible",
            message="This saved test cannot be opened safely. Contact support before changing it.",
        ) from exc
    return TestResponse.model_validate(
        {
            **state.model_dump(mode="json", by_alias=True),
            "id": test.id,
            "status": test.status,
            "stateVersion": test.state_version,
            "createdAt": test.created_at,
            "updatedAt": test.updated_at,
        }
    )


async def get_owned_test(
    db: AsyncSession,
    test_id: str,
    owner_session_id: str,
    *,
    for_update: bool = False,
) -> TestRun:
    statement = select(TestRun).where(
        TestRun.id == test_id,
        TestRun.owner_session_id == owner_session_id,
    )
    if for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    result = await db.execute(statement)
    test = result.scalar_one_or_none()
    if test is None:
        raise test_not_found()
    return test


async def lock_test(db: AsyncSession, test_id: str) -> TestRun:
    test = await db.scalar(
        select(TestRun)
        .where(TestRun.id == test_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if test is None:
        raise test_not_found()
    return test
