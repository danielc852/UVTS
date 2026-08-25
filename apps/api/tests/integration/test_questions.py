from collections.abc import AsyncIterator, Callable
from typing import cast
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import SecretStr
from sqlalchemy import event

import uvts_api.api.dispatch as operation_dispatch
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


def review_items(question_set: dict[str, object]) -> list[dict[str, str]]:
    items = cast(list[dict[str, str]], question_set["items"])
    return [{"id": item["id"], "text": item["text"]} for item in items]


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
    generated = await client.post(f"/api/v1/tests/{test_id}/questions")
    items = review_items(generated.json()["questionSet"])

    confirmed = await client.post(
        f"/api/v1/tests/{test_id}/questions/confirm",
        json={"items": items},
    )

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
    reconfirm = await client.post(
        f"/api/v1/tests/{test_id}/questions/confirm",
        json={"items": items},
    )
    assert reconfirm.status_code == 409
    assert reconfirm.json()["error"]["code"] == "question_set_confirmed"


async def test_confirmation_applies_edits_and_additions_in_submitted_order(
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
) -> None:
    client, _, _ = generation_client
    test_id = await configured_test(client)
    generated = await client.post(f"/api/v1/tests/{test_id}/questions")
    draft = generated.json()["questionSet"]
    original = review_items(draft)
    submitted = [
        {"id": original[1]["id"], "text": "  Edited second question?  "},
        {"id": original[0]["id"], "text": original[0]["text"]},
        {"text": "  What should I do after setup?  "},
        {"id": original[2]["id"], "text": original[2]["text"]},
    ]

    confirmed = await client.post(
        f"/api/v1/tests/{test_id}/questions/confirm",
        json={"items": submitted},
    )

    assert confirmed.status_code == 200
    items = confirmed.json()["questionSet"]["items"]
    assert [item["text"] for item in items] == [
        "Edited second question?",
        original[0]["text"],
        "What should I do after setup?",
        original[2]["text"],
    ]
    assert [items[0]["id"], items[1]["id"], items[3]["id"]] == [
        original[1]["id"],
        original[0]["id"],
        original[2]["id"],
    ]
    assert items[2]["id"] not in {item["id"] for item in original}
    UUID(items[2]["id"])


@pytest.mark.parametrize(
    "invalid_items",
    [
        lambda items: [*items[:1], {**items[1], "text": "   "}, *items[2:]],
        lambda items: [*items, {"text": f"  {items[0]['text'].upper()}  "}],
        lambda items: [{**items[0], "id": "unknown-question"}, *items[1:]],
        lambda items: [items[0], items[0], *items[1:]],
        lambda items: items[:-1],
    ],
    ids=["blank", "normalized-duplicate", "unknown-id", "duplicate-id", "missing-id"],
)
async def test_invalid_review_is_rejected_without_changing_the_draft(
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
    invalid_items: Callable[
        [list[dict[str, str]]],
        list[dict[str, str]],
    ],
) -> None:
    client, _, notifications = generation_client
    test_id = await configured_test(client)
    generated = await client.post(f"/api/v1/tests/{test_id}/questions")
    before = generated.json()
    items = review_items(before["questionSet"])
    notifications.published.clear()

    response = await client.post(
        f"/api/v1/tests/{test_id}/questions/confirm",
        json={"items": invalid_items(items)},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "question_review_invalid"
    current = (await client.get(f"/api/v1/tests/{test_id}")).json()
    assert current["questionSet"] == before["questionSet"]
    assert current["status"] == before["status"]
    assert current["stateVersion"] == before["stateVersion"]
    assert notifications.published == []


async def test_confirmation_enforces_the_fifteen_question_limit(
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
) -> None:
    client, _, _ = generation_client
    test_id = await configured_test(client)
    generated = await client.post(f"/api/v1/tests/{test_id}/questions")
    draft = generated.json()
    items = review_items(draft["questionSet"])
    fifteen = [*items, *({"text": f"Added question {number}?"} for number in range(12))]

    accepted = await client.post(
        f"/api/v1/tests/{test_id}/questions/confirm",
        json={"items": fifteen},
    )

    assert accepted.status_code == 200
    assert len(accepted.json()["questionSet"]["items"]) == 15

    other_test_id = await configured_test(client)
    other_generated = await client.post(f"/api/v1/tests/{other_test_id}/questions")
    other_before = other_generated.json()
    other_items = review_items(other_before["questionSet"])
    sixteen = [
        *other_items,
        *({"text": f"Extra question {number}?"} for number in range(13)),
    ]
    rejected = await client.post(
        f"/api/v1/tests/{other_test_id}/questions/confirm",
        json={"items": sixteen},
    )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"
    current = (await client.get(f"/api/v1/tests/{other_test_id}")).json()
    assert current["questionSet"] == other_before["questionSet"]


async def test_confirmation_rejects_a_stale_draft_without_changing_it(
    app: FastAPI,
    generation_client: tuple[AsyncClient, FakeStructuredChatModel, RecordingNotifications],
) -> None:
    client, _, notifications = generation_client
    test_id = await configured_test(client)
    generated = await client.post(f"/api/v1/tests/{test_id}/questions")
    items = review_items(generated.json()["questionSet"])
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        state = dict(test.state)
        configuration = dict(state["configuration"])
        configuration["version"] += 1
        state["configuration"] = configuration
        test.state = state
        await db.commit()
    before = (await client.get(f"/api/v1/tests/{test_id}")).json()
    notifications.published.clear()

    response = await client.post(
        f"/api/v1/tests/{test_id}/questions/confirm",
        json={"items": items},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "question_set_stale"
    current = (await client.get(f"/api/v1/tests/{test_id}")).json()
    assert current["questionSet"] == before["questionSet"]
    assert current["stateVersion"] == before["stateVersion"]
    assert notifications.published == []


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
