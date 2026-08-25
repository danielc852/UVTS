import json
import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from uvts_api.ports.notifications import StateNotifications
from uvts_api.services.tests import get_owned_test, to_test_response


def encode_sse(*, event: str, event_id: int, data: object) -> str:
    return (
        f"id: {event_id}\n"
        f"event: {event}\n"
        f"data: {json.dumps(data, separators=(',', ':'), default=str)}\n\n"
    )


async def publish_test_change(
    notifications: StateNotifications,
    test_id: str,
    *,
    logger: logging.Logger,
    failure_message: str,
) -> None:
    try:
        await notifications.publish(test_id)
    except Exception:
        logger.warning(
            failure_message,
            extra={"test_id": test_id},
            exc_info=True,
        )


async def stream_test_events(
    *,
    test_id: str,
    owner_session_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    notifications: StateNotifications,
) -> AsyncIterator[str]:
    last_version = 0

    async def refetch() -> str | None:
        nonlocal last_version
        async with session_factory() as db:
            test = await get_owned_test(db, test_id, owner_session_id)
            if test.state_version <= last_version:
                return None
            response = await to_test_response(db, test)
            last_version = test.state_version
            return encode_sse(
                event="test.updated",
                event_id=last_version,
                data=response.model_dump(mode="json", by_alias=True),
            )

    initial = await refetch()
    if initial:
        yield initial
    async for _ in notifications.listen(test_id):
        changed = await refetch()
        if changed:
            yield changed
        else:
            yield ": heartbeat\n\n"
