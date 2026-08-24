from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from httpx import AsyncClient

from tests.integration.test_question_configuration import create_setup
from uvts_api.adapters.db.models import TestRun as RunModel
from uvts_api.ports.question_generator import QUESTION_GENERATION_INSTRUCTIONS
from uvts_api.schemas.workspace import (
    ManualStatus,
    ManualSummary,
    QuestionSet,
    QuestionSetSource,
    QuestionSetStatus,
    WorkflowStage,
    WorkspaceState,
)
from uvts_api.services.question_generation import build_question_generation_input


async def test_agent_input_contains_only_saved_product_context(
    app: FastAPI, client: AsyncClient, tmp_path: Path
) -> None:
    del tmp_path
    created_response = await create_setup(
        client,
        image=("product.png", b"private-product-image", "image/png"),
        description="  A portable weather sensor.  ",
        total_questions=6,
    )
    created = created_response.json()
    test_id = str(created["id"])

    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        request = await build_question_generation_input(
            db=db,
            storage=app.state.document_storage,
            test=test,
        )

    assert set(request.__dict__) == {
        "product_image",
        "product_description",
        "question_design",
        "instructions",
    }
    assert request.product_image.content == b"private-product-image"
    assert request.product_image.content_type == "image/png"
    assert request.product_image.filename == "product.png"
    assert request.product_description == "A portable weather sensor."
    assert request.question_design.total_questions == 6
    assert request.instructions == QUESTION_GENERATION_INSTRUCTIONS
    assert "manual" not in request.__dict__
    assert "Do not answer" in request.instructions


async def test_confirmation_does_not_trust_a_stale_manual_summary(
    app: FastAPI, client: AsyncClient
) -> None:
    created = await create_setup(client, total_questions=1)
    test_id = str(created.json()["id"])
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        state = WorkspaceState.model_validate(test.state)
        state = state.model_copy(
            update={
                "current_stage": WorkflowStage.QUESTIONS,
                "manual": ManualSummary(
                    id="missing-manual",
                    filename="missing.pdf",
                    page_count=1,
                    status=ManualStatus.READY,
                ),
                "question_set": QuestionSet(
                    id="set-1",
                    status=QuestionSetStatus.DRAFT,
                    source=QuestionSetSource.PRODUCT_CONTEXT,
                    configuration_version=state.configuration.version,
                    generated_at=datetime.now(UTC),
                    items=[{"id": "q1", "text": "How do I start?"}],
                ),
            }
        )
        test.state = state.model_dump(mode="json", by_alias=True)
        test.status = "questions_ready"
        await db.commit()

    confirmed = await client.post(f"/api/v1/tests/{test_id}/questions/confirm")

    assert confirmed.status_code == 200
    assert confirmed.json()["currentStage"] == "upload"
    assert confirmed.json()["status"] == "questions_confirmed"
