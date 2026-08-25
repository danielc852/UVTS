from collections import defaultdict, deque
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from typing import cast

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import BaseModel
from sqlalchemy import select

import uvts_api.api.operation_dispatch as operation_dispatch
from uvts_api.adapters.db.models import (
    AnonymousSession,
    Document,
    QuestionEvaluationRecord,
)
from uvts_api.adapters.db.models import TestRun as RunModel
from uvts_api.agents.evaluator import EvaluatorAgent
from uvts_api.agents.schemas import QuestionEvaluationOutput, ReportSynthesisOutput
from uvts_api.domain.enums import TestStatus as RunStatus
from uvts_api.schemas.workspace import (
    ManualStatus,
    ManualSummary,
    Question,
    QuestionSet,
    QuestionSetSource,
    QuestionSetStatus,
    WorkflowStage,
    WorkspaceState,
)
from uvts_api.services.evaluation import process_evaluation_operation, start_evaluation


class FakeStructuredModel:
    def __init__(self, model: "FakeChatModel", schema: type[BaseModel]) -> None:
        self.model = model
        self.schema = schema

    async def ainvoke(self, messages: list[BaseMessage]) -> object:
        self.model.calls.append((self.schema, messages))
        if self.model.before_invoke is not None:
            callback, self.model.before_invoke = self.model.before_invoke, None
            await callback()
        value = self.model.responses[self.schema].popleft()
        if isinstance(value, Exception):
            raise value
        return value


class FakeChatModel:
    def __init__(self) -> None:
        self.responses: defaultdict[type[BaseModel], deque[object]] = defaultdict(deque)
        self.calls: list[tuple[type[BaseModel], list[BaseMessage]]] = []
        self.before_invoke: Callable[[], Awaitable[None]] | None = None

    def with_structured_output(
        self,
        schema: type[BaseModel],
        *,
        method: str,
        strict: bool,
    ) -> FakeStructuredModel:
        assert method == "json_schema"
        assert strict is True
        return FakeStructuredModel(self, schema)


def make_question(question_id: str) -> Question:
    return Question(
        id=question_id,
        text=f"What information is available for {question_id}?",
    )


async def prepare_evaluation_api(app: FastAPI, fake: FakeChatModel) -> None:
    app.state.settings = app.state.settings.model_copy(
        update={"agent_processing_eager": True}
    )
    app.state.chat_model = fake


async def seed_ready_test(
    app: FastAPI,
    client: AsyncClient,
    *,
    questions: list[Question],
) -> str:
    await client.post("/api/v1/session")
    async with app.state.session_factory() as db:
        owner = (await db.scalars(select(AnonymousSession))).one()
        manual = ManualSummary(
            id="manual-1",
            filename="guide.pdf",
            page_count=1,
            status=ManualStatus.READY,
        )
        state = WorkspaceState.model_validate(
            {
                "schemaVersion": 2,
                "currentStage": WorkflowStage.EVALUATION,
                "manual": manual,
                "questionSet": QuestionSet(
                    id="question-set-1",
                    status=QuestionSetStatus.CONFIRMED,
                    source=QuestionSetSource.LEGACY_MANUAL,
                    configuration_version=None,
                    confirmed_at=datetime.now(UTC),
                    items=questions,
                ),
            }
        )
        test = RunModel(
            owner_session_id=owner.id,
            status=RunStatus.READY.value,
            state=state.model_dump(mode="json", by_alias=True),
        )
        db.add(test)
        await db.flush()
        db.add(
            Document(
                id=manual.id,
                test_run_id=test.id,
                role="active",
                filename=manual.filename,
                storage_key=f"{test.id}.pdf",
                status=ManualStatus.READY.value,
                page_count=1,
                pages=[
                    {
                        "page": 1,
                        "text": "Setup is complete. Follow the recovery steps.",
                    }
                ],
            )
        )
        await db.commit()
        return test.id


async def test_evaluation_continues_after_failure_and_retry_preserves_completed_result(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    fake = FakeChatModel()
    await prepare_evaluation_api(app, fake)
    questions = [make_question("q1"), make_question("q2")]
    test_id = await seed_ready_test(app, client, questions=questions)
    fake.responses[QuestionEvaluationOutput].extend(
        [
            {
                "status": "found",
                "information_needed": "Setup state",
                "information_found": "Setup is complete",
                "information_missing": None,
                "evidence": [{"page": 1, "extract": "Setup is complete."}],
            },
            RuntimeError("provider request included private details"),
        ]
    )

    evaluated = await client.post(f"/api/v1/tests/{test_id}/evaluation")

    assert evaluated.status_code == 202
    body = evaluated.json()
    assert body["status"] == "incomplete"
    assert body["currentStage"] == "report"
    assert body["evaluation"] == [
        {"questionId": "q1", "status": "complete", "error": None},
        {
            "questionId": "q2",
            "status": "failed",
            "error": "The question could not be checked. Try this question again.",
        },
    ]
    assert [result["status"] for result in body["report"]["results"]] == [
        "found",
        "failed",
    ]
    assert body["report"]["counts"] == {
        "found": 1,
        "partly_found": 0,
        "not_found": 0,
        "failed": 1,
    }

    fake.responses[QuestionEvaluationOutput].append(
        {
            "status": "not_found",
            "information_needed": "A recovery limit",
            "information_found": None,
            "information_missing": "The recovery limit",
            "evidence": [],
        }
    )
    fake.responses[ReportSynthesisOutput].append(valid_synthesis("q2"))
    retried = await client.post(f"/api/v1/tests/{test_id}/evaluation/q2/retry")

    assert retried.status_code == 202
    retry_body = retried.json()
    assert retry_body["status"] == "complete"
    assert retry_body["report"]["isComplete"] is True
    assert retry_body["report"]["counts"] == {
        "found": 1,
        "partly_found": 0,
        "not_found": 1,
        "failed": 0,
    }
    assert retry_body["report"]["results"][0] == body["report"]["results"][0]
    assert retry_body["report"]["recommendations"][0]["gapId"] == "gap-1"
    async with app.state.session_factory() as db:
        records = list(
            (
                await db.scalars(
                    select(QuestionEvaluationRecord).order_by(
                        QuestionEvaluationRecord.question_id
                    )
                )
            ).all()
        )
    assert [(record.question_id, record.attempt) for record in records] == [
        ("q1", 1),
        ("q2", 2),
    ]


async def test_report_failure_retains_results_and_report_retry_does_not_rerun_questions(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    fake = FakeChatModel()
    await prepare_evaluation_api(app, fake)
    test_id = await seed_ready_test(app, client, questions=[make_question("q1")])
    fake.responses[QuestionEvaluationOutput].append(
        {
            "status": "not_found",
            "information_needed": "Recovery details",
            "information_found": None,
            "information_missing": "Recovery details",
            "evidence": [],
        }
    )
    fake.responses[ReportSynthesisOutput].append(RuntimeError("provider unavailable"))

    evaluated = await client.post(f"/api/v1/tests/{test_id}/evaluation")

    assert evaluated.status_code == 202
    body = evaluated.json()
    assert body["status"] == "incomplete"
    assert body["report"]["results"][0]["status"] == "not_found"
    assert body["report"]["gaps"] == []
    assert body["error"] == {
        "code": "report_synthesis_failed",
        "title": "The report is incomplete",
        "message": (
            "Question results were saved, but UVTS could not finish the report. "
            "Try finishing the report again."
        ),
        "stage": "report",
        "retryable": True,
    }

    fake.responses[ReportSynthesisOutput].append(valid_synthesis("q1"))
    retried = await client.post(f"/api/v1/tests/{test_id}/report/retry")

    assert retried.status_code == 202
    retry_body = retried.json()
    assert retry_body["status"] == "complete"
    assert retry_body["error"] is None
    assert retry_body["report"]["gaps"][0]["affectedQuestionIds"] == ["q1"]
    assert [schema for schema, _ in fake.calls].count(QuestionEvaluationOutput) == 1
    async with app.state.session_factory() as db:
        record = (await db.scalars(select(QuestionEvaluationRecord))).one()
        assert record.attempt == 1


async def test_retry_failed_endpoint_processes_only_failures_sequentially(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    fake = FakeChatModel()
    await prepare_evaluation_api(app, fake)
    test_id = await seed_ready_test(
        app,
        client,
        questions=[make_question("q1"), make_question("q2")],
    )
    fake.responses[QuestionEvaluationOutput].extend(
        [RuntimeError("first"), RuntimeError("second")]
    )
    first = await client.post(f"/api/v1/tests/{test_id}/evaluation")
    assert first.status_code == 202
    assert first.json()["report"]["counts"]["failed"] == 2

    fake.responses[QuestionEvaluationOutput].extend(
        [
            {
                "status": "found",
                "information_needed": "Setup state",
                "information_found": "Setup is complete",
                "information_missing": None,
                "evidence": [{"page": 1, "extract": "Setup is complete."}],
            },
            {
                "status": "found",
                "information_needed": "Recovery steps",
                "information_found": "Recovery steps exist",
                "information_missing": None,
                "evidence": [{"page": 1, "extract": "Follow the recovery steps."}],
            },
        ]
    )
    retried = await client.post(
        f"/api/v1/tests/{test_id}/evaluation/retry-failed"
    )

    assert retried.status_code == 202
    assert retried.json()["report"]["counts"] == {
        "found": 2,
        "partly_found": 0,
        "not_found": 0,
        "failed": 0,
    }
    assert [item["status"] for item in retried.json()["evaluation"]] == [
        "complete",
        "complete",
    ]


async def test_stale_operation_cannot_write_a_model_result(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    fake = FakeChatModel()
    test_id = await seed_ready_test(app, client, questions=[make_question("q1")])
    fake.responses[QuestionEvaluationOutput].append(
        {
            "status": "found",
            "information_needed": "Setup state",
            "information_found": "Setup is complete",
            "information_missing": None,
            "evidence": [{"page": 1, "extract": "Setup is complete."}],
        }
    )
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        operation_id, question_ids = await start_evaluation(
            db=db,
            test=test,
            agent_settings={"provider": "openrouter", "model": "test-model"},
        )

        async def replace_operation() -> None:
            async with app.state.session_factory() as competing_db:
                competing_test = await competing_db.get(RunModel, test_id)
                assert competing_test is not None
                competing_test.active_operation_id = "new-operation"
                await competing_db.commit()

        fake.before_invoke = replace_operation
        await process_evaluation_operation(
            db=db,
            storage=app.state.document_storage,
            agent=EvaluatorAgent(cast(BaseChatModel, fake)),
            notifications=app.state.notifications,
            test_id=test_id,
            operation_id=operation_id,
            question_ids=question_ids,
        )

    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        record = (await db.scalars(select(QuestionEvaluationRecord))).one()
        assert test is not None
        assert test.active_operation_id == "new-operation"
        assert test.state["evaluation"][0]["status"] == "checking"
        assert test.state["report"] is None
        assert record.status == "checking"
        assert record.result is None
        assert record.attempt == 1


async def test_queue_failure_clears_operation_and_keeps_retry_path(
    app: FastAPI,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_id = await seed_ready_test(app, client, questions=[make_question("q1")])
    app.state.settings = app.state.settings.model_copy(
        update={"agent_processing_eager": False}
    )

    def fail_enqueue(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(operation_dispatch, "enqueue_evaluation_processing", fail_enqueue)

    response = await client.post(f"/api/v1/tests/{test_id}/evaluation")

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "incomplete"
    assert body["error"]["code"] == "evaluation_dispatch_failed"
    assert body["evaluation"][0]["status"] == "failed"
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        assert test.active_operation_id is None


async def test_non_eager_evaluation_queues_the_operation_arguments(
    app: FastAPI,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_id = await seed_ready_test(app, client, questions=[make_question("q1")])
    app.state.settings = app.state.settings.model_copy(
        update={"agent_processing_eager": False}
    )
    dispatched: list[tuple[str, str, list[str]]] = []

    def record_enqueue(
        queued_test_id: str,
        operation_id: str,
        question_ids: Sequence[str],
    ) -> None:
        dispatched.append((queued_test_id, operation_id, list(question_ids)))

    monkeypatch.setattr(
        operation_dispatch,
        "enqueue_evaluation_processing",
        record_enqueue,
    )

    response = await client.post(f"/api/v1/tests/{test_id}/evaluation")

    assert response.status_code == 202
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        assert dispatched == [(test_id, test.active_operation_id, ["q1"])]


def valid_synthesis(question_id: str) -> dict[str, object]:
    return {
        "gaps": [
            {
                "key": "recovery",
                "title": "Missing recovery detail",
                "why_it_matters": "Users need to recover without starting again.",
                "affected_question_ids": [question_id],
                "kind": "missing",
            }
        ],
        "recommendations": [
            {
                "priority": "High",
                "change": "Add the missing recovery detail.",
                "reason": "The tested question could not find it.",
                "gap_key": "recovery",
            }
        ],
        "follow_up_questions": ["Can setup recover without starting again?"],
    }
