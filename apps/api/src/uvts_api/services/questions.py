import logging
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from uvts_api.adapters.ai.openrouter import build_openrouter_model
from uvts_api.adapters.db.models import Document, TestRun
from uvts_api.agents.question_agent import QuestionAgent
from uvts_api.core.config import Settings
from uvts_api.core.errors import AppError, test_not_found
from uvts_api.domain.enums import TestStatus
from uvts_api.ports.notifications import StateNotifications
from uvts_api.schemas.workspace import (
    ManualStatus,
    TestConfiguration,
    WorkflowStage,
    WorkspaceError,
    WorkspaceState,
)
from uvts_api.services.documents import update_state

logger = logging.getLogger(__name__)

QUESTION_AGENT_TEMPERATURE = 0.0


@dataclass(frozen=True)
class GenerationOperation:
    test_id: str
    operation_id: str


def build_question_agent(settings: Settings) -> QuestionAgent:
    return QuestionAgent(
        build_openrouter_model(settings, temperature=QUESTION_AGENT_TEMPERATURE)
    )


async def begin_question_generation(
    *,
    db: AsyncSession,
    notifications: StateNotifications,
    test: TestRun,
    configuration: TestConfiguration,
    settings: Settings,
) -> GenerationOperation:
    locked_test = await db.scalar(
        select(TestRun)
        .where(TestRun.id == test.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locked_test is None:
        raise test_not_found()
    test = locked_test
    state = WorkspaceState.model_validate(test.state)
    _ensure_generation_allowed(test, state)
    await _get_ready_manual(db, test, state)

    operation = GenerationOperation(test_id=test.id, operation_id=str(uuid4()))
    test.status = TestStatus.GENERATING.value
    test.active_operation_id = operation.operation_id
    agent_settings = dict(test.agent_settings)
    agent_settings["questionAgent"] = {
        "provider": "openrouter",
        "model": settings.openrouter_model,
        "temperature": QUESTION_AGENT_TEMPERATURE,
        "requestTimeoutSeconds": settings.openrouter_request_timeout_seconds,
        "maxRetries": 2,
    }
    test.agent_settings = agent_settings
    update_state(
        test,
        state.model_copy(
            update={
                "configuration": configuration,
                "error": None,
            }
        ),
    )
    await db.commit()
    await publish_question_change(notifications, test.id)
    return operation


async def process_question_generation(
    *,
    db: AsyncSession,
    notifications: StateNotifications,
    agent: QuestionAgent,
    test_id: str,
    operation_id: str,
) -> None:
    test = await db.get(TestRun, test_id)
    if test is None or not _operation_is_active(test, operation_id):
        return

    try:
        state = WorkspaceState.model_validate(test.state)
        manual = await _get_ready_manual(db, test, state)
        manual_text = page_labelled_manual_text(manual.pages)
        questions = await agent.generate(
            manual_text=manual_text,
            configuration=state.configuration,
        )
    except Exception as error:
        await fail_question_generation(
            db=db,
            notifications=notifications,
            test_id=test_id,
            operation_id=operation_id,
            error=error,
        )
        return

    await db.refresh(test)
    if not _operation_is_active(test, operation_id):
        return
    state = WorkspaceState.model_validate(test.state)
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": WorkflowStage.QUESTIONS,
                "questions": questions,
                "evaluation": [],
                "report": None,
                "error": None,
            }
        ),
    )
    test.status = TestStatus.QUESTIONS_READY.value
    test.active_operation_id = None
    await db.commit()
    await publish_question_change(notifications, test.id)


async def fail_question_generation(
    *,
    db: AsyncSession,
    notifications: StateNotifications,
    test_id: str,
    operation_id: str,
    error: Exception,
) -> None:
    await db.rollback()
    test = await db.get(TestRun, test_id)
    if test is None or not _operation_is_active(test, operation_id):
        return

    state = WorkspaceState.model_validate(test.state)
    error_stage = (
        WorkflowStage.QUESTIONS if state.questions else WorkflowStage.CONFIGURATION
    )
    update_state(
        test,
        state.model_copy(
            update={
                "error": WorkspaceError(
                    code="question_generation_failed",
                    title="Questions were not created",
                    message="UVTS could not create the questions. Try again.",
                    stage=error_stage,
                    retryable=True,
                )
            }
        ),
    )
    test.status = TestStatus.FAILED.value
    test.active_operation_id = None
    await db.commit()
    logger.warning(
        "Question generation failed",
        extra={
            "test_id": test.id,
            "operation_id": operation_id,
            "error_type": type(error).__name__,
        },
    )
    await publish_question_change(notifications, test.id)


def page_labelled_manual_text(pages: list[dict[str, Any]]) -> str:
    labelled_pages: list[str] = []
    has_text = False
    for page in pages:
        page_number = page.get("page")
        text = page.get("text")
        if not isinstance(page_number, int) or page_number < 1 or not isinstance(text, str):
            raise ValueError("The stored manual pages are invalid.")
        has_text = has_text or bool(text.strip())
        labelled_pages.append(f"[Page {page_number}]\n{text}")
    if not labelled_pages or not has_text:
        raise ValueError("The stored manual does not contain readable text.")
    return "\n\n".join(labelled_pages)


async def publish_question_change(
    notifications: StateNotifications, test_id: str
) -> None:
    try:
        await notifications.publish(test_id)
    except Exception:
        logger.warning(
            "Question state notification failed",
            extra={"test_id": test_id},
            exc_info=True,
        )


def _ensure_generation_allowed(test: TestRun, state: WorkspaceState) -> None:
    if test.active_operation_id is not None:
        raise AppError(
            status_code=409,
            code="operation_in_progress",
            message="Wait for the current operation to finish before trying again.",
            retryable=True,
        )

    if state.manual_upload is not None:
        raise AppError(
            status_code=409,
            code="manual_upload_in_progress",
            message="Wait for the current PDF check to finish before generating questions.",
            retryable=True,
        )

    allowed = {
        (TestStatus.DRAFT.value, WorkflowStage.CONFIGURATION),
        (TestStatus.QUESTIONS_READY.value, WorkflowStage.QUESTIONS),
        (TestStatus.FAILED.value, WorkflowStage.CONFIGURATION),
        (TestStatus.FAILED.value, WorkflowStage.QUESTIONS),
    }
    if (
        (test.status, state.current_stage) not in allowed
        or bool(state.evaluation)
        or state.report is not None
    ):
        raise AppError(
            status_code=409,
            code="question_generation_not_allowed",
            message="Questions cannot be generated at this stage of the test.",
        )


async def _get_ready_manual(
    db: AsyncSession, test: TestRun, state: WorkspaceState
) -> Document:
    manual = await db.scalar(
        select(Document).where(
            Document.test_run_id == test.id,
            Document.role == "active",
        )
    )
    if (
        manual is None
        or manual.status != ManualStatus.READY.value
        or state.manual is None
        or state.manual.id != manual.id
    ):
        raise AppError(
            status_code=409,
            code="manual_not_ready",
            message="Add a ready manual before generating questions.",
        )
    return manual


def _operation_is_active(test: TestRun, operation_id: str) -> bool:
    return bool(
        test.active_operation_id == operation_id
        and test.status == TestStatus.GENERATING.value
    )
