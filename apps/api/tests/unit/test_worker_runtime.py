from pathlib import Path
from typing import Self, cast

import pytest

from uvts_api.core.config import Settings
from uvts_api.workers import documents, evaluation, questions
from uvts_api.workers import runtime as worker_runtime
from uvts_api.workers.celery_app import celery_app
from uvts_api.workers.settings import settings_for_agent


class FakeEngine:
    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


class FakeRedis:
    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        self.closed = True


@pytest.fixture
def runtime_resources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Settings, FakeEngine, FakeRedis, FakeSession]:
    settings = Settings(
        database_url="sqlite+aiosqlite://",
        redis_url="redis://unused/0",
        sse_heartbeat_seconds=2.5,
    ).model_copy(update={"storage_root": tmp_path / "documents"})
    engine = FakeEngine()
    redis = FakeRedis()
    session = FakeSession()

    monkeypatch.setattr(worker_runtime, "get_settings", lambda: settings)
    monkeypatch.setattr(worker_runtime, "create_engine", lambda database_url: engine)
    monkeypatch.setattr(worker_runtime, "create_session_factory", lambda value: lambda: session)
    monkeypatch.setattr(
        "uvts_api.workers.runtime.Redis.from_url",
        lambda redis_url, *, decode_responses: redis,
    )
    return settings, engine, redis, session


async def test_open_worker_runtime_builds_shared_task_resources(
    runtime_resources: tuple[Settings, FakeEngine, FakeRedis, FakeSession],
) -> None:
    settings, engine, redis, session = runtime_resources

    async with worker_runtime.open_worker_runtime() as resources:
        assert resources.settings is settings
        assert cast(object, resources.db) is session
        assert resources.storage._root == settings.storage_root.resolve()
        assert cast(object, resources.notifications._redis) is redis
        assert resources.notifications._heartbeat_seconds == 2.5
        assert not engine.disposed
        assert not redis.closed
        assert not session.closed

    assert session.closed
    assert redis.closed
    assert engine.disposed


async def test_open_worker_runtime_cleans_up_after_task_failure(
    runtime_resources: tuple[Settings, FakeEngine, FakeRedis, FakeSession],
) -> None:
    _, engine, redis, session = runtime_resources

    with pytest.raises(RuntimeError, match="task failed"):
        async with worker_runtime.open_worker_runtime():
            raise RuntimeError("task failed")

    assert session.closed
    assert redis.closed
    assert engine.disposed


def test_worker_task_names_and_dispatch_arguments_are_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispatched: list[tuple[str, list[object]]] = []
    monkeypatch.setattr(
        celery_app,
        "send_task",
        lambda name, *, args: dispatched.append((name, args)),
    )

    documents.enqueue_document_processing("document-1")
    questions.enqueue_question_generation("test-1", "operation-1")
    evaluation.enqueue_evaluation_processing(
        "test-1",
        "operation-2",
        ("question-1", "question-2"),
    )

    assert documents.process_document.name == "uvts.documents.process"
    assert questions.generate_questions.name == "uvts.questions.generate"
    assert evaluation.process_evaluation.name == "uvts.evaluation.process"
    assert dispatched == [
        ("uvts.documents.process", ["document-1"]),
        ("uvts.questions.generate", ["test-1", "operation-1"]),
        (
            "uvts.evaluation.process",
            ["test-1", "operation-2", ["question-1", "question-2"]],
        ),
    ]


def test_workers_restore_recorded_agent_settings_without_mutating_defaults() -> None:
    settings = Settings(
        openrouter_model="current-default",
        openrouter_fallback_model="current-fallback",
        openrouter_request_timeout_seconds=60,
    )
    recorded_settings = {
        "questionAgent": {
            "model": "recorded-question-model",
            "fallbackModel": "recorded-question-fallback",
            "requestTimeoutSeconds": 25,
        },
        "evaluator": {
            "model": "recorded-evaluator-model",
            "fallbackModel": "recorded-evaluator-fallback",
            "requestTimeoutSeconds": 35,
        },
    }

    question_settings = settings_for_agent(
        settings,
        recorded_settings,
        agent="questionAgent",
    )
    evaluator_settings = settings_for_agent(
        settings,
        recorded_settings,
        agent="evaluator",
    )

    assert question_settings.openrouter_model == "recorded-question-model"
    assert question_settings.openrouter_fallback_model == "recorded-question-fallback"
    assert question_settings.openrouter_request_timeout_seconds == 25
    assert evaluator_settings.openrouter_model == "recorded-evaluator-model"
    assert evaluator_settings.openrouter_fallback_model == "recorded-evaluator-fallback"
    assert evaluator_settings.openrouter_request_timeout_seconds == 35
    assert settings.openrouter_model == "current-default"
    assert settings.openrouter_fallback_model == "current-fallback"
    assert settings.openrouter_request_timeout_seconds == 60


@pytest.mark.parametrize(
    "recorded_settings",
    [
        None,
        {},
        {"evaluator": "not-an-object"},
    ],
)
def test_recorded_agent_settings_fall_back_to_defaults(
    recorded_settings: dict[str, object] | None,
) -> None:
    settings = Settings(
        openrouter_model="current-default",
        openrouter_fallback_model="current-fallback",
        openrouter_request_timeout_seconds=60,
    )

    restored = settings_for_agent(settings, recorded_settings, agent="evaluator")

    assert restored is settings


def test_recorded_agent_settings_ignore_invalid_values() -> None:
    settings = Settings(
        openrouter_model="current-default",
        openrouter_fallback_model="current-fallback",
        openrouter_request_timeout_seconds=60,
    )

    restored = settings_for_agent(
        settings,
        {
            "evaluator": {
                "model": " ",
                "fallbackModel": " ",
                "requestTimeoutSeconds": True,
            }
        },
        agent="evaluator",
    )

    assert restored.openrouter_model == "current-default"
    assert restored.openrouter_fallback_model == ""
    assert restored.openrouter_request_timeout_seconds == 60
