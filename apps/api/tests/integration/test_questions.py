from collections.abc import AsyncIterator
from pathlib import Path
from typing import cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langchain_core.language_models.chat_models import BaseChatModel

from tests.fake_models import FakeStructuredChatModel
from tests.pdf_helpers import write_pdf
from uvts_api.adapters.db.models import TestRun as RunModel
from uvts_api.agents.question_agent import QuestionAgent
from uvts_api.agents.schemas import GeneratedQuestion, GeneratedQuestionSet
from uvts_api.api.routes import questions as question_routes
from uvts_api.domain.enums import TestStatus as RunStatus
from uvts_api.schemas.workspace import QuestionType, Viewpoint, WorkflowStage, WorkspaceState


class RecordingNotifications:
    def __init__(self) -> None:
        self.published: list[str] = []

    async def publish(self, test_id: str) -> None:
        self.published.append(test_id)

    async def listen(self, test_id: str) -> AsyncIterator[None]:
        del test_id
        if False:
            yield


def generated_questions() -> GeneratedQuestionSet:
    return GeneratedQuestionSet(
        questions=[
            GeneratedQuestion(
                text="How do I begin?",
                type=QuestionType.BASIC,
                topic="Setup and requirements",
                viewpoint=Viewpoint.BEGINNER,
            ),
            GeneratedQuestion(
                text="Where are the main requirements listed?",
                type=QuestionType.BASIC,
                topic="Setup and requirements",
                viewpoint=Viewpoint.REGULAR_USER,
            ),
            GeneratedQuestion(
                text="What if a setup step cannot finish?",
                type=QuestionType.EDGE_CASE,
                topic="Troubleshooting and recovery",
                viewpoint=Viewpoint.ADVANCED_USER,
            ),
        ]
    )


def request_configuration() -> dict[str, object]:
    return {
        "totalQuestions": 3,
        "typeCounts": {"basic": 2, "crossParagraph": 0, "edgeCase": 1},
        "topics": ["Setup and requirements", "Troubleshooting and recovery"],
        "viewpoints": ["Beginner", "Regular user", "Advanced user"],
    }


@pytest.fixture
async def generation_client(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications]]:
    model = FakeStructuredChatModel(generated_questions())
    notifications = RecordingNotifications()
    app.state.settings.agent_processing_eager = True
    app.state.notifications = notifications
    monkeypatch.setattr(
        question_routes,
        "build_question_agent",
        lambda settings: QuestionAgent(cast(BaseChatModel, model)),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client, model, notifications


async def upload_ready_manual(
    client: AsyncClient, tmp_path: Path, filename: str = "guide.pdf"
) -> str:
    path = write_pdf(tmp_path / filename)
    with path.open("rb") as pdf:
        response = await client.post(
            "/api/v1/tests/manual",
            files={"file": (filename, pdf, "application/pdf")},
        )
    assert response.status_code == 202
    return str(response.json()["id"])


async def test_generation_saves_questions_settings_and_state_changes(
    app: FastAPI,
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
    tmp_path: Path,
) -> None:
    client, model, notifications = generation_client
    await client.post("/api/v1/session")
    test_id = await upload_ready_manual(client, tmp_path)
    notifications.published.clear()

    response = await client.post(
        f"/api/v1/tests/{test_id}/questions",
        json=request_configuration(),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "questions_ready"
    assert body["currentStage"] == "questions"
    assert len(body["questions"]) == 3
    assert len({question["id"] for question in body["questions"]}) == 3
    assert body["evaluation"] == []
    assert body["report"] is None
    assert body["error"] is None
    assert notifications.published == [test_id, test_id]
    assert "[Page 1]\nReadable page 1" in str(model.invocations[0][1].content)

    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        assert test.active_operation_id is None
        assert test.agent_settings == {
            "questionAgent": {
                "provider": "openrouter",
                "model": app.state.settings.openrouter_model,
                "temperature": 0.0,
                "requestTimeoutSeconds": 60,
                "maxRetries": 2,
            }
        }


async def test_failed_regeneration_preserves_questions_and_is_retryable(
    app: FastAPI,
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
    tmp_path: Path,
) -> None:
    client, model, notifications = generation_client
    await client.post("/api/v1/session")
    test_id = await upload_ready_manual(client, tmp_path)
    first = await client.post(
        f"/api/v1/tests/{test_id}/questions",
        json=request_configuration(),
    )
    original_questions = first.json()["questions"]
    model.response = RuntimeError("provider included sensitive details")
    notifications.published.clear()

    failed = await client.post(
        f"/api/v1/tests/{test_id}/questions",
        json=request_configuration(),
    )

    assert failed.status_code == 202
    body = failed.json()
    assert body["status"] == "failed"
    assert body["currentStage"] == "questions"
    assert body["questions"] == original_questions
    assert body["error"] == {
        "code": "question_generation_failed",
        "title": "Questions were not created",
        "message": "UVTS could not create the questions. Try again.",
        "stage": "questions",
        "retryable": True,
    }
    assert "sensitive details" not in body["error"]["message"]
    assert notifications.published == [test_id, test_id]
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        assert test.active_operation_id is None


async def test_initial_generation_failure_keeps_configuration_ready_to_retry(
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
    tmp_path: Path,
) -> None:
    client, model, notifications = generation_client
    await client.post("/api/v1/session")
    test_id = await upload_ready_manual(client, tmp_path)
    model.response = RuntimeError("temporary provider failure")
    notifications.published.clear()

    failed = await client.post(
        f"/api/v1/tests/{test_id}/questions",
        json=request_configuration(),
    )

    assert failed.status_code == 202
    body = failed.json()
    assert body["status"] == "failed"
    assert body["currentStage"] == "configuration"
    assert body["configuration"] == request_configuration()
    assert body["questions"] == []
    assert body["error"]["stage"] == "configuration"
    assert body["error"]["retryable"] is True
    assert notifications.published == [test_id, test_id]


async def test_generation_conflicts_do_not_start_another_operation(
    app: FastAPI,
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
    tmp_path: Path,
) -> None:
    client, model, notifications = generation_client
    del model, notifications
    await client.post("/api/v1/session")
    test_id = await upload_ready_manual(client, tmp_path)

    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        test.active_operation_id = "already-running"
        await db.commit()
    active = await client.post(
        f"/api/v1/tests/{test_id}/questions", json=request_configuration()
    )
    assert active.status_code == 409
    assert active.json()["error"]["code"] == "operation_in_progress"

    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        state = WorkspaceState.model_validate(test.state)
        test.active_operation_id = None
        test.status = RunStatus.EVALUATING.value
        test.state = state.model_copy(
            update={"current_stage": WorkflowStage.EVALUATION}
        ).model_dump(mode="json", by_alias=True)
        await db.commit()
    wrong_stage = await client.post(
        f"/api/v1/tests/{test_id}/questions", json=request_configuration()
    )
    assert wrong_stage.status_code == 409
    assert wrong_stage.json()["error"]["code"] == "question_generation_not_allowed"


async def test_generation_requires_a_ready_owned_manual(
    app: FastAPI,
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
) -> None:
    client, model, notifications = generation_client
    del model, notifications
    created = await client.post("/api/v1/session")
    assert created.status_code == 200
    no_manual = await client.post(
        "/api/v1/tests",
        json={"currentStage": "configuration", "questions": [], "evaluation": []},
    )
    missing = await client.post(
        f"/api/v1/tests/{no_manual.json()['id']}/questions",
        json=request_configuration(),
    )
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "manual_not_ready"

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as stranger:
        await stranger.post("/api/v1/session")
        hidden = await stranger.post(
            f"/api/v1/tests/{no_manual.json()['id']}/questions",
            json=request_configuration(),
        )
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "test_not_found"


async def test_non_eager_generation_returns_durable_active_state(
    app: FastAPI,
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, model, notifications = generation_client
    del model
    await client.post("/api/v1/session")
    test_id = await upload_ready_manual(client, tmp_path)
    notifications.published.clear()
    app.state.settings.agent_processing_eager = False
    dispatched: list[tuple[str, str]] = []
    monkeypatch.setattr(
        question_routes,
        "enqueue_question_generation",
        lambda queued_test_id, operation_id: dispatched.append(
            (queued_test_id, operation_id)
        ),
    )

    response = await client.post(
        f"/api/v1/tests/{test_id}/questions", json=request_configuration()
    )

    assert response.status_code == 202
    assert response.json()["status"] == "generating"
    assert len(dispatched) == 1
    assert dispatched[0][0] == test_id
    assert notifications.published == [test_id]
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        assert test.active_operation_id == dispatched[0][1]


async def test_queue_failure_clears_operation_and_returns_retryable_state(
    app: FastAPI,
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, model, notifications = generation_client
    del model
    await client.post("/api/v1/session")
    test_id = await upload_ready_manual(client, tmp_path)
    notifications.published.clear()
    app.state.settings.agent_processing_eager = False

    def fail_to_queue(test_id: str, operation_id: str) -> None:
        del test_id, operation_id
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(
        question_routes,
        "enqueue_question_generation",
        fail_to_queue,
    )

    response = await client.post(
        f"/api/v1/tests/{test_id}/questions", json=request_configuration()
    )

    assert response.status_code == 202
    assert response.json()["status"] == "failed"
    assert response.json()["error"]["retryable"] is True
    assert notifications.published == [test_id, test_id]
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        assert test.active_operation_id is None
