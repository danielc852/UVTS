import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from uvts_api.adapters.ai.openrouter import build_openrouter_model, is_openrouter_configured
from uvts_api.adapters.db.models import Document, QuestionEvaluationRecord, TestRun
from uvts_api.agents.question_agent import QuestionAgent
from uvts_api.core.config import Settings
from uvts_api.core.errors import AppError
from uvts_api.domain.enums import TestStatus
from uvts_api.ports.notifications import StateNotifications
from uvts_api.ports.question_generator import GeneratedQuestionSet, QuestionGenerator
from uvts_api.ports.storage import DocumentStorage
from uvts_api.schemas.workspace import (
    ManualStatus,
    Question,
    QuestionSet,
    QuestionSetSource,
    QuestionSetStatus,
    WorkflowStage,
    WorkspaceError,
    WorkspaceState,
)
from uvts_api.services.documents import delete_storage_after_commit, update_state
from uvts_api.services.events import publish_test_change
from uvts_api.services.question_generation import build_question_generation_input
from uvts_api.services.tests import lock_test

logger = logging.getLogger(__name__)
QUESTION_AGENT_TEMPERATURE = 0.0


@dataclass(frozen=True)
class GenerationOperation:
    test_id: str
    operation_id: str


def build_question_agent(settings: Settings) -> QuestionAgent:
    return QuestionAgent(build_openrouter_model(settings, temperature=QUESTION_AGENT_TEMPERATURE))


async def begin_question_generation(
    *,
    db: AsyncSession,
    notifications: StateNotifications,
    test: TestRun,
    settings: Settings,
) -> GenerationOperation:
    test = await lock_test(db, test.id)
    state = WorkspaceState.model_validate(test.state)
    _ensure_generation_allowed(test, state)
    if not is_openrouter_configured(settings):
        raise AppError(
            status_code=503,
            code="openrouter_api_key_required",
            message=(
                "An OpenRouter API key is required to generate questions. "
                "Add OPENROUTER_API_KEY to the server environment and restart UVTS."
            ),
        )

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
    update_state(test, state.model_copy(update={"error": None}))
    await db.commit()
    await publish_question_change(notifications, test.id)
    return operation


async def process_question_generation(
    *,
    db: AsyncSession,
    storage: DocumentStorage,
    notifications: StateNotifications,
    agent: QuestionGenerator,
    test_id: str,
    operation_id: str,
) -> None:
    test = await db.get(TestRun, test_id)
    if test is None or not _operation_is_active(test, operation_id):
        return

    try:
        request = await build_question_generation_input(db=db, storage=storage, test=test)
        generated = await agent.generate(request)
        question_texts = validate_generated_questions(
            generated,
            expected_count=request.question_design.total_questions,
        )
        questions = [Question(id=str(uuid4()), text=text) for text in question_texts]
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
    question_set = QuestionSet(
        id=str(uuid4()),
        status=QuestionSetStatus.DRAFT,
        source=QuestionSetSource.PRODUCT_CONTEXT,
        configuration_version=state.configuration.version,
        generated_at=datetime.now(UTC),
        confirmed_at=None,
        items=questions,
    )
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": WorkflowStage.QUESTIONS,
                "question_set": question_set,
                "evaluation_source": None,
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
    error_stage = WorkflowStage.QUESTIONS if state.question_set else WorkflowStage.CONFIGURATION
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": error_stage,
                "error": WorkspaceError(
                    code="question_generation_failed",
                    title="Questions were not created",
                    message="UVTS could not create the questions. Try again.",
                    stage=error_stage,
                    retryable=True,
                ),
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


async def confirm_questions(*, db: AsyncSession, test: TestRun) -> None:
    test = await lock_test(db, test.id)
    state = WorkspaceState.model_validate(test.state)
    if test.active_operation_id is not None:
        raise _operation_in_progress()
    question_set = state.question_set
    if question_set is None:
        raise AppError(
            status_code=409,
            code="question_set_not_ready",
            message="Generate questions before confirming them.",
        )
    if question_set.status == QuestionSetStatus.CONFIRMED:
        raise AppError(
            status_code=409,
            code="question_set_confirmed",
            message="These questions are already confirmed.",
        )
    if question_set.source != QuestionSetSource.PRODUCT_CONTEXT:
        raise AppError(
            status_code=409,
            code="question_set_not_confirmable",
            message=(
                "Generate a new set from Product setup before confirming these legacy questions."
            ),
        )
    if question_set.configuration_version != state.configuration.version:
        raise AppError(
            status_code=409,
            code="question_set_stale",
            message="Generate a new set after the latest Product setup changes.",
        )

    ready_manual = None
    if state.manual is not None and state.manual.status == ManualStatus.READY:
        ready_manual = await db.scalar(
            select(Document).where(
                Document.id == state.manual.id,
                Document.test_run_id == test.id,
                Document.role == "active",
                Document.status == ManualStatus.READY.value,
            )
        )
    manual_ready = ready_manual is not None
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": (
                    WorkflowStage.EVALUATION if manual_ready else WorkflowStage.UPLOAD
                ),
                "question_set": question_set.model_copy(
                    update={
                        "status": QuestionSetStatus.CONFIRMED,
                        "confirmed_at": datetime.now(UTC),
                    }
                ),
                "error": None,
            }
        ),
    )
    test.status = TestStatus.READY.value if manual_ready else TestStatus.QUESTIONS_CONFIRMED.value
    await db.commit()


async def start_over(*, db: AsyncSession, storage: DocumentStorage, test: TestRun) -> None:
    test = await lock_test(db, test.id)
    if test.active_operation_id is not None:
        raise _operation_in_progress()
    state = WorkspaceState.model_validate(test.state)
    documents = list(
        (
            await db.scalars(
                select(Document).where(
                    Document.test_run_id == test.id,
                    Document.role.in_(("active", "pending")),
                )
            )
        ).all()
    )
    storage_keys = [document.storage_key for document in documents]
    for document in documents:
        await db.delete(document)
    await db.execute(
        delete(QuestionEvaluationRecord).where(QuestionEvaluationRecord.test_run_id == test.id)
    )
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": WorkflowStage.CONFIGURATION,
                "manual": None,
                "manual_upload": None,
                "question_set": None,
                "evaluation_source": None,
                "evaluation": [],
                "report": None,
                "error": None,
            }
        ),
    )
    test.status = TestStatus.DRAFT.value
    test.active_operation_id = None
    test.agent_settings = {}
    await db.commit()
    for storage_key in storage_keys:
        await delete_storage_after_commit(storage, storage_key)


async def publish_question_change(notifications: StateNotifications, test_id: str) -> None:
    await publish_test_change(
        notifications,
        test_id,
        logger=logger,
        failure_message="Question state notification failed",
    )


def _ensure_generation_allowed(test: TestRun, state: WorkspaceState) -> None:
    if test.active_operation_id is not None:
        raise _operation_in_progress()
    if state.question_set is not None and state.question_set.status == QuestionSetStatus.CONFIRMED:
        raise AppError(
            status_code=409,
            code="question_set_confirmed",
            message="Start over before generating different questions.",
        )
    configuration = state.configuration
    if configuration.product_image is None or not configuration.product_description.strip():
        raise AppError(
            status_code=409,
            code="question_configuration_incomplete",
            message="Save a product image and description before creating questions.",
        )
    if state.evaluation or state.report is not None:
        raise AppError(
            status_code=409,
            code="question_generation_not_allowed",
            message="Questions cannot be generated at this stage of the test.",
        )


def validate_generated_questions(
    generated: GeneratedQuestionSet,
    *,
    expected_count: int,
) -> list[str]:
    """Validate provider output at the application boundary before assigning IDs."""

    if len(generated.questions) != expected_count:
        raise ValueError("The generated total does not match the request.")
    normalized: set[str] = set()
    question_texts: list[str] = []
    for item in generated.questions:
        text = item.text.strip()
        if not text:
            raise ValueError("A generated question is empty.")
        key = " ".join(
            part
            for part in re.split(r"[^\w]+", unicodedata.normalize("NFKC", text).casefold())
            if part
        )
        if not key or key in normalized:
            raise ValueError("The generated questions are not unique.")
        normalized.add(key)
        question_texts.append(text)
    return question_texts


def _operation_in_progress() -> AppError:
    return AppError(
        status_code=409,
        code="operation_in_progress",
        message="Wait for the current operation to finish before trying again.",
        retryable=True,
    )


def _operation_is_active(test: TestRun, operation_id: str) -> bool:
    return bool(
        test.active_operation_id == operation_id and test.status == TestStatus.GENERATING.value
    )
