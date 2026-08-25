from collections.abc import AsyncIterator
from typing import cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import SecretStr
from sqlalchemy import event

import uvts_api.api.operation_dispatch as operation_dispatch
from tests.fake_models import FakeStructuredChatModel
from tests.integration.test_question_configuration import create_setup, save_setup
from uvts_api.adapters.db.models import Document
from uvts_api.adapters.db.models import TestRun as RunModel
from uvts_api.agents.question_agent import QuestionAgent
from uvts_api.ports.question_generator import GeneratedQuestion, GeneratedQuestionSet


class RecordingNotifications:
    def __init__(self) -> None:
        self.published: list[str] = []

    async def publish(self, test_id: str) -> None:
        self.published.append(test_id)

    async def listen(self, test_id: str) -> AsyncIterator[None]:
        del test_id
        if False:
            yield


def generated_questions(prefix: str = "") -> GeneratedQuestionSet:
    return GeneratedQuestionSet(
        questions=[
            GeneratedQuestion(text=f"{prefix}How do I begin?"),
            GeneratedQuestion(text=f"{prefix}Where are the main requirements listed?"),
            GeneratedQuestion(text=f"{prefix}What if a setup step cannot finish?"),
        ]
    )


@pytest.fixture
async def generation_client(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications]]:
    model = FakeStructuredChatModel(generated_questions())
    notifications = RecordingNotifications()
    app.state.settings.agent_processing_eager = True
    app.state.settings.openrouter_api_key = SecretStr("test-openrouter-key")
    app.state.notifications = notifications
    monkeypatch.setattr(
        operation_dispatch,
        "build_question_agent",
        lambda settings: QuestionAgent(cast(BaseChatModel, model)),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client, model, notifications


async def configured_test(client: AsyncClient) -> str:
    response = await create_setup(
        client,
        image=("product.png", b"private-product-image", "image/png"),
        description="A portable weather sensor.",
        total_questions=3,
    )
    assert response.status_code == 201
    return str(response.json()["id"])


async def test_generation_needs_no_manual_and_persists_a_draft_set(
    app: FastAPI,
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
) -> None:
    client, model, notifications = generation_client
    test_id = await configured_test(client)
    notifications.published.clear()

    # A retained legacy manual may coexist with Product setup during migration.
    # Generation must ignore that row and its extracted page text completely.
    async with app.state.session_factory() as db:
        db.add(
            Document(
                test_run_id=test_id,
                role="active",
                filename="legacy.pdf",
                storage_key="legacy-manual.pdf",
                status="ready",
                page_count=1,
                pages=[{"page": 1, "text": "POISONED MANUAL CONTENT"}],
            )
        )
        await db.commit()
    statement_parameters: list[object] = []

    def record_sql(
        connection: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        del connection, cursor, statement, context, executemany
        statement_parameters.append(parameters)

    event.listen(app.state.engine.sync_engine, "before_cursor_execute", record_sql)

    try:
        response = await client.post(f"/api/v1/tests/{test_id}/questions")
    finally:
        event.remove(app.state.engine.sync_engine, "before_cursor_execute", record_sql)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "questions_ready"
    assert body["currentStage"] == "questions"
    assert body["manual"] is None
    assert body["questionSet"]["status"] == "draft"
    assert body["questionSet"]["source"] == "product_context_v1"
    assert body["questionSet"]["configurationVersion"] == 1
    assert len(body["questionSet"]["items"]) == 3
    assert notifications.published == [test_id, test_id]
    rendered = str(model.invocations[0][1].content)
    assert "A portable weather sensor." in rendered
    assert "image" in rendered
    assert "manual" not in rendered.casefold()
    assert "POISONED MANUAL CONTENT" not in rendered
    assert all("active" not in repr(parameters) for parameters in statement_parameters)
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        assert test.active_operation_id is None


async def test_generation_requires_an_openrouter_api_key_without_starting_work(
    app: FastAPI,
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
) -> None:
    client, model, notifications = generation_client
    test_id = await configured_test(client)
    app.state.settings.openrouter_api_key = SecretStr("   ")
    notifications.published.clear()

    response = await client.post(f"/api/v1/tests/{test_id}/questions")

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "openrouter_api_key_required",
        "message": (
            "An OpenRouter API key is required to generate questions. "
            "Add OPENROUTER_API_KEY to the server environment and restart UVTS."
        ),
        "retryable": False,
        "field_errors": None,
        "details": None,
    }
    assert model.invocations == []
    assert notifications.published == []
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        assert test.status == "draft"
        assert test.active_operation_id is None


async def test_failed_regeneration_preserves_the_previous_draft(
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
) -> None:
    client, model, notifications = generation_client
    test_id = await configured_test(client)
    first = await client.post(f"/api/v1/tests/{test_id}/questions")
    original = first.json()["questionSet"]
    model.response = RuntimeError("provider included sensitive details")
    notifications.published.clear()

    failed = await client.post(f"/api/v1/tests/{test_id}/questions")

    assert failed.status_code == 202
    body = failed.json()
    assert body["status"] == "failed"
    assert body["currentStage"] == "questions"
    assert body["questionSet"] == original
    assert body["error"]["code"] == "question_generation_failed"
    assert "sensitive details" not in body["error"]["message"]
    assert notifications.published == [test_id, test_id]


async def test_confirmation_is_persisted_and_locks_setup_and_generation(
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
) -> None:
    client, _, _ = generation_client
    test_id = await configured_test(client)
    await client.post(f"/api/v1/tests/{test_id}/questions")

    confirmed = await client.post(f"/api/v1/tests/{test_id}/questions/confirm")

    assert confirmed.status_code == 200
    body = confirmed.json()
    assert body["status"] == "questions_confirmed"
    assert body["currentStage"] == "upload"
    assert body["questionSet"]["status"] == "confirmed"
    assert body["questionSet"]["confirmedAt"] is not None

    generation_locked = await client.post(f"/api/v1/tests/{test_id}/questions")
    setup_locked = await save_setup(client, test_id)
    assert generation_locked.status_code == 409
    assert generation_locked.json()["error"]["code"] == "question_set_confirmed"
    assert setup_locked.status_code == 409
    assert setup_locked.json()["error"]["code"] == "configuration_locked"


async def test_generation_is_owned_and_rejects_parallel_work(
    app: FastAPI,
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
) -> None:
    client, _, _ = generation_client
    test_id = await configured_test(client)
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        test.active_operation_id = "already-running"
        await db.commit()
    active = await client.post(f"/api/v1/tests/{test_id}/questions")
    assert active.status_code == 409
    assert active.json()["error"]["code"] == "operation_in_progress"

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as stranger:
        await stranger.post("/api/v1/session")
        hidden = await stranger.post(f"/api/v1/tests/{test_id}/questions")
    assert hidden.status_code == 404


async def test_non_eager_generation_returns_a_durable_active_operation(
    app: FastAPI,
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, notifications = generation_client
    test_id = await configured_test(client)
    notifications.published.clear()
    app.state.settings.agent_processing_eager = False
    dispatched: list[tuple[str, str]] = []
    monkeypatch.setattr(
        operation_dispatch,
        "enqueue_question_generation",
        lambda queued_test_id, operation_id: dispatched.append((queued_test_id, operation_id)),
    )

    response = await client.post(f"/api/v1/tests/{test_id}/questions")

    assert response.status_code == 202
    assert response.json()["status"] == "generating"
    assert dispatched[0][0] == test_id
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        assert test.active_operation_id == dispatched[0][1]


async def test_queue_failure_clears_the_operation_and_keeps_retry_path(
    app: FastAPI,
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = generation_client
    test_id = await configured_test(client)
    app.state.settings.agent_processing_eager = False

    def fail_to_queue(test_id: str, operation_id: str) -> None:
        del test_id, operation_id
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(operation_dispatch, "enqueue_question_generation", fail_to_queue)
    response = await client.post(f"/api/v1/tests/{test_id}/questions")

    assert response.status_code == 202
    assert response.json()["status"] == "failed"
    assert response.json()["error"]["retryable"] is True
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        assert test.active_operation_id is None
