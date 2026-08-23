from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from uvts_api.adapters.db.models import TestRun
from uvts_api.core.errors import test_not_found
from uvts_api.schemas.tests import TestResponse
from uvts_api.schemas.workspace import WorkspaceState


def to_test_response(test: TestRun) -> TestResponse:
    state = WorkspaceState.model_validate(test.state)
    return TestResponse(
        id=test.id,
        status=test.status,
        state_version=test.state_version,
        created_at=test.created_at,
        updated_at=test.updated_at,
        **state.model_dump(),
    )


async def get_owned_test(db: AsyncSession, test_id: str, owner_session_id: str) -> TestRun:
    result = await db.execute(
        select(TestRun).where(
            TestRun.id == test_id,
            TestRun.owner_session_id == owner_session_id,
        )
    )
    test = result.scalar_one_or_none()
    if test is None:
        raise test_not_found()
    return test
