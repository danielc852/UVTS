from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select

import uvts_api.api.operation_dispatch as operation_dispatch
from tests.integration.test_question_configuration import create_setup
from tests.pdf_helpers import write_pdf
from uvts_api.adapters.db.models import Document, QuestionEvaluationRecord
from uvts_api.adapters.db.models import TestRun as RunModel
from uvts_api.schemas.workspace import (
    QuestionSet,
    QuestionSetSource,
    QuestionSetStatus,
    WorkflowStage,
    WorkspaceState,
)


async def create_confirmed_test(app: FastAPI, client: AsyncClient) -> tuple[str, dict[str, object]]:
    created = await create_setup(client, total_questions=1)
    assert created.status_code == 201
    test_id = str(created.json()["id"])
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        state = WorkspaceState.model_validate(test.state)
        question_set = QuestionSet(
            id="question-set-1",
            status=QuestionSetStatus.CONFIRMED,
            source=QuestionSetSource.PRODUCT_CONTEXT,
            configuration_version=state.configuration.version,
            confirmed_at=datetime.now(UTC),
            items=[{"id": "q1", "text": "How do I start?"}],
        )
        state = state.model_copy(
            update={"current_stage": WorkflowStage.UPLOAD, "question_set": question_set}
        )
        test.state = state.model_dump(mode="json", by_alias=True)
        test.status = "questions_confirmed"
        await db.commit()
    return test_id, created.json()["configuration"]


async def upload_manual(client: AsyncClient, test_id: str, path: Path) -> Response:
    with path.open("rb") as pdf:
        return await client.put(
            f"/api/v1/tests/{test_id}/manual",
            files={"file": (path.name, pdf, "application/pdf")},
        )


async def seed_report_lineage(app: FastAPI, test_id: str) -> dict[str, object]:
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        state = WorkspaceState.model_validate(test.state)
        assert state.question_set is not None and state.manual is not None
        source = {
            "questionSetId": state.question_set.id,
            "manualId": state.manual.id,
        }
        raw = state.model_dump(mode="json", by_alias=True)
        raw["currentStage"] = "report"
        raw["evaluationSource"] = source
        raw["evaluation"] = [{"questionId": "q1", "status": "complete", "error": None}]
        raw["report"] = {
            "source": source,
            "isComplete": True,
            "counts": {"found": 1, "partly_found": 0, "not_found": 0, "failed": 0},
            "results": [
                {
                    "question": {"id": "q1", "text": "How do I start?"},
                    "status": "found",
                    "informationNeeded": "Setup instructions",
                    "informationFound": "Readable page 1",
                    "informationMissing": None,
                    "evidence": [{"page": 1, "extract": "Readable page 1"}],
                }
            ],
            "gaps": [],
            "recommendations": [],
            "followUpQuestions": [],
        }
        test.state = WorkspaceState.model_validate(raw).model_dump(mode="json", by_alias=True)
        test.status = "complete"
        test.agent_settings = {
            "questionAgent": {"model": "question-model"},
            "evaluator": {"model": "evaluation-model"},
        }
        db.add(
            QuestionEvaluationRecord(
                test_run_id=test.id,
                question_id="q1",
                question_set_id=state.question_set.id,
                manual_id=state.manual.id,
                status="complete",
                result={"status": "found"},
                attempt=1,
            )
        )
        await db.commit()
        return raw


async def test_attach_view_range_and_remove_manual_preserves_confirmed_questions(
    client: AsyncClient, app: FastAPI, tmp_path: Path
) -> None:
    test_id, configuration = await create_confirmed_test(app, client)
    source = write_pdf(tmp_path / "guide.pdf", pages=2)

    uploaded = await upload_manual(client, test_id, source)

    assert uploaded.status_code == 202
    body = uploaded.json()
    assert body["currentStage"] == "evaluation"
    assert body["status"] == "ready"
    assert body["manual"]["pageCount"] == 2
    assert body["questionSet"]["status"] == "confirmed"

    content = await client.get(f"/api/v1/tests/{test_id}/manual/content")
    partial = await client.get(
        f"/api/v1/tests/{test_id}/manual/content", headers={"Range": "bytes=0-7"}
    )
    assert content.status_code == 200
    assert content.headers["cache-control"] == "private, no-store"
    assert partial.status_code == 206

    deleted = await client.delete(f"/api/v1/tests/{test_id}/manual")
    assert deleted.status_code == 200
    deleted_body = deleted.json()
    assert deleted_body["currentStage"] == "upload"
    assert deleted_body["configuration"] == configuration
    assert deleted_body["questionSet"] == body["questionSet"]
    assert deleted_body["manual"] is None


async def test_non_eager_upload_queues_the_pending_document(
    app: FastAPI,
    client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_id, _ = await create_confirmed_test(app, client)
    source = write_pdf(tmp_path / "queued.pdf")
    app.state.settings.document_processing_eager = False
    dispatched: list[str] = []
    monkeypatch.setattr(operation_dispatch, "enqueue_document_processing", dispatched.append)

    uploaded = await upload_manual(client, test_id, source)

    assert uploaded.status_code == 202
    assert uploaded.json()["status"] == "questions_confirmed"
    async with app.state.session_factory() as db:
        document = (
            await db.scalars(
                select(Document).where(
                    Document.test_run_id == test_id,
                    Document.role == "pending",
                )
            )
        ).one()
        assert dispatched == [document.id]


async def test_manual_upload_is_locked_until_confirmation_and_is_private(
    app: FastAPI, client: AsyncClient, tmp_path: Path
) -> None:
    created = await create_setup(client)
    unconfirmed_id = str(created.json()["id"])
    source = write_pdf(tmp_path / "private.pdf")
    locked = await upload_manual(client, unconfirmed_id, source)
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "manual_locked"

    test_id, _ = await create_confirmed_test(app, client)
    await upload_manual(client, test_id, source)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as stranger:
        await stranger.post("/api/v1/session")
        hidden = await stranger.get(f"/api/v1/tests/{test_id}/manual/content")
    assert hidden.status_code == 404


async def test_failed_replacement_preserves_the_complete_previous_lineage(
    app: FastAPI, client: AsyncClient, tmp_path: Path
) -> None:
    test_id, _ = await create_confirmed_test(app, client)
    valid = write_pdf(tmp_path / "valid.pdf")
    locked = write_pdf(tmp_path / "locked.pdf", encrypted=True)
    created = await upload_manual(client, test_id, valid)
    await seed_report_lineage(app, test_id)
    previous = (await client.get(f"/api/v1/tests/{test_id}")).json()

    replaced = await upload_manual(client, test_id, locked)

    assert replaced.status_code == 202
    body = replaced.json()
    for key in (
        "status",
        "currentStage",
        "manual",
        "configuration",
        "questionSet",
        "evaluationSource",
        "evaluation",
        "report",
    ):
        assert body[key] == previous[key]
    assert body["error"]["code"] == "manual_password_protected"
    assert body["manual"]["id"] == created.json()["manual"]["id"]


async def test_successful_replacement_preserves_questions_and_clears_only_manual_results(
    app: FastAPI, client: AsyncClient, tmp_path: Path
) -> None:
    test_id, configuration = await create_confirmed_test(app, client)
    original = write_pdf(tmp_path / "original.pdf")
    replacement = write_pdf(tmp_path / "replacement.pdf", pages=2)
    created = await upload_manual(client, test_id, original)
    original_question_set = created.json()["questionSet"]
    original_manual_id = created.json()["manual"]["id"]
    await seed_report_lineage(app, test_id)

    replaced = await upload_manual(client, test_id, replacement)

    assert replaced.status_code == 202
    body = replaced.json()
    assert body["status"] == "ready"
    assert body["currentStage"] == "evaluation"
    assert body["configuration"] == configuration
    assert body["questionSet"] == original_question_set
    assert body["manual"]["id"] != original_manual_id
    assert body["evaluationSource"] is None
    assert body["evaluation"] == []
    assert body["report"] is None
    async with app.state.session_factory() as db:
        records = list((await db.scalars(select(QuestionEvaluationRecord))).all())
        test = await db.get(RunModel, test_id)
        assert records == []
        assert test is not None
        assert "questionAgent" in test.agent_settings
        assert "evaluator" not in test.agent_settings


async def test_initial_processing_failure_returns_to_upload_and_cleans_candidate(
    app: FastAPI, client: AsyncClient, tmp_path: Path
) -> None:
    test_id, _ = await create_confirmed_test(app, client)
    scanned = write_pdf(tmp_path / "scan.pdf", with_text=False)

    uploaded = await upload_manual(client, test_id, scanned)

    assert uploaded.status_code == 202
    body = uploaded.json()
    assert body["status"] == "questions_confirmed"
    assert body["currentStage"] == "upload"
    assert body["manual"] is None
    assert body["questionSet"]["status"] == "confirmed"
    assert body["error"]["code"] == "manual_no_readable_text"


async def test_manual_changes_wait_for_active_agent_work(
    app: FastAPI, client: AsyncClient, tmp_path: Path
) -> None:
    test_id, _ = await create_confirmed_test(app, client)
    original = write_pdf(tmp_path / "active-original.pdf")
    replacement = write_pdf(tmp_path / "active-replacement.pdf")
    await upload_manual(client, test_id, original)
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        test.active_operation_id = "operation-in-progress"
        await db.commit()

    replaced = await upload_manual(client, test_id, replacement)
    deleted = await client.delete(f"/api/v1/tests/{test_id}/manual")
    assert replaced.status_code == 409
    assert deleted.status_code == 409


async def test_start_over_keeps_product_setup_and_removes_the_entire_later_lineage(
    app: FastAPI, client: AsyncClient, tmp_path: Path
) -> None:
    test_id, configuration = await create_confirmed_test(app, client)
    original = write_pdf(tmp_path / "start-over.pdf")
    await upload_manual(client, test_id, original)
    await seed_report_lineage(app, test_id)

    reset = await client.post(f"/api/v1/tests/{test_id}/start-over")

    assert reset.status_code == 200
    body = reset.json()
    assert body["id"] == test_id
    assert body["status"] == "draft"
    assert body["currentStage"] == "configuration"
    assert body["configuration"] == configuration
    assert body["questionSet"] is None
    assert body["manual"] is None
    assert body["evaluationSource"] is None
    assert body["evaluation"] == []
    assert body["report"] is None
    async with app.state.session_factory() as db:
        records = list((await db.scalars(select(QuestionEvaluationRecord))).all())
        test = await db.get(RunModel, test_id)
        assert records == []
        assert test is not None and test.agent_settings == {}
