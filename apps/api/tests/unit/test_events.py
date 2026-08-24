from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from sqlalchemy import update

from uvts_api.adapters.db.models import AnonymousSession
from uvts_api.adapters.db.models import TestRun as DbTestRun
from uvts_api.services.events import stream_test_events


class OneUpdateNotification:
    def __init__(self, update_state: Callable[[str], Awaitable[None]]) -> None:
        self._update_state = update_state

    async def publish(self, test_id: str) -> None:
        return None

    async def listen(self, test_id: str) -> AsyncIterator[None]:
        await self._update_state(test_id)
        yield None


async def test_sse_refetches_persisted_state_after_notification(app: FastAPI) -> None:
    async with app.state.session_factory() as db:
        owner = AnonymousSession(
            token_hash="a" * 64,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        db.add(owner)
        await db.flush()
        test = DbTestRun(
            owner_session_id=owner.id,
            state={
                "currentStage": "upload",
                "configuration": {
                    "totalQuestions": 9,
                    "typeCounts": {"basic": 3, "crossParagraph": 3, "edgeCase": 3},
                    "topics": ["Setup and requirements"],
                    "viewpoints": ["Beginner"],
                },
                "questions": [],
                "evaluation": [],
            },
        )
        db.add(test)
        await db.commit()
        test_id, owner_id = test.id, owner.id

    async def persist_change(changed_test_id: str) -> None:
        async with app.state.session_factory() as db:
            await db.execute(
                update(DbTestRun)
                .where(DbTestRun.id == changed_test_id)
                .values(
                    state={
                        "currentStage": "evaluation",
                        "configuration": {
                            "totalQuestions": 9,
                            "typeCounts": {
                                "basic": 3,
                                "crossParagraph": 3,
                                "edgeCase": 3,
                            },
                            "topics": ["Setup and requirements"],
                            "viewpoints": ["Beginner"],
                        },
                        "questions": [],
                        "evaluation": [],
                    },
                    state_version=2,
                )
            )
            await db.commit()

    events = stream_test_events(
        test_id=test_id,
        owner_session_id=owner_id,
        session_factory=app.state.session_factory,
        notifications=OneUpdateNotification(persist_change),
    )
    first = await anext(events)
    second = await anext(events)

    assert "id: 1" in first and '"currentStage":"configuration"' in first
    assert "id: 2" in second and '"currentStage":"evaluation"' in second
