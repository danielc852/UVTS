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
from uvts_api.agents.question_generation import QuestionAgent
from uvts_api.core.config import Settings
from uvts_api.core.errors import AppError
from uvts_api.domain.enums import TestStatus
from uvts_api.ports.notifications import StateNotifications
from uvts_api.ports.question_generator import (
    GeneratedQuestionSet,
    GenerationMode,
    QuestionGenerator,
)
from uvts_api.ports.storage import DocumentStorage
from uvts_api.schemas.questions import ConfirmQuestionItem
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
from uvts_api.services.documents import delete_storage_after_commit
from uvts_api.services.events import publish_test_change
from uvts_api.services.question_generation import build_question_generation_input
from uvts_api.services.tests import lock_test
from uvts_api.services.workspace import load_workspace_state, update_state

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
    state = await load_workspace_state(db, test)
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
        "fallbackModel": settings.openrouter_fallback_model,
        "temperature": QUESTION_AGENT_TEMPERATURE,
        "requestTimeoutSeconds": settings.openrouter_request_timeout_seconds,
        "maxRetries": 2,
    }
    test.agent_settings = agent_settings
    update_state(
        test,
        state.model_copy(
            update={"current_stage": WorkflowStage.QUESTIONS, "error": None}
        ),
    )
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
    state = await load_workspace_state(db, test)
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
    state = await load_workspace_state(db, test)
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


async def confirm_questions(
    *,
    db: AsyncSession,
    test: TestRun,
    items: list[ConfirmQuestionItem],
) -> None:
    test = await lock_test(db, test.id)
    state = await load_workspace_state(db, test)
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

    reviewed_questions = _validate_reviewed_questions(question_set, items)

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
                        "items": reviewed_questions,
                    }
                ),
                "error": None,
            }
        ),
    )
    test.status = TestStatus.READY.value if manual_ready else TestStatus.QUESTIONS_CONFIRMED.value
    await db.commit()


async def suggest_question(
    *,
    db: AsyncSession,
    storage: DocumentStorage,
    test: TestRun,
    settings: Settings,
    direction: str,
    existing_questions: list[str],
    agent: QuestionGenerator | None = None,
) -> str:
    """Generate one reviewable question without changing the saved draft."""

    state = await load_workspace_state(db, test)
    _ensure_suggestion_allowed(test, state)
    if not is_openrouter_configured(settings):
        raise AppError(
            status_code=503,
            code="openrouter_api_key_required",
            message=(
                "An OpenRouter API key is required to generate a question. "
                "Add OPENROUTER_API_KEY to the server environment and restart UVTS."
            ),
        )
    clean_direction = direction.strip()
    if not clean_direction:
        raise AppError(
            status_code=422,
            code="question_direction_required",
            message="Describe the kind of question you want UVTS to create.",
            field_errors={"direction": ["Enter a direction for the question."]},
        )
    clean_existing = tuple(question.strip() for question in existing_questions if question.strip())
    try:
        question_agent = agent or build_question_agent(settings)
        request = await build_question_generation_input(
            db=db,
            storage=storage,
            test=test,
            total_questions=1,
            mode=GenerationMode.SUGGESTION,
            direction=clean_direction,
            existing_questions=clean_existing,
        )
        generated = await question_agent.generate(request)
        suggestion = validate_generated_questions(generated, expected_count=1)[0]
        existing_keys = {_normalized_question_key(question) for question in clean_existing}
        if _normalized_question_key(suggestion) in existing_keys:
            raise ValueError("The suggested question duplicates the current draft.")
        return suggestion
    except AppError:
        raise
    except Exception as error:
        logger.warning(
            "Question suggestion failed",
            extra={"test_id": test.id, "error_type": type(error).__name__},
        )
        raise AppError(
            status_code=502,
            code="question_suggestion_failed",
            message="UVTS could not generate a question. Try again.",
            retryable=True,
        ) from None


async def start_over(*, db: AsyncSession, storage: DocumentStorage, test: TestRun) -> None:
    test = await lock_test(db, test.id)
    if test.active_operation_id is not None:
        raise _operation_in_progress()
    state = await load_workspace_state(db, test)
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


def _ensure_suggestion_allowed(test: TestRun, state: WorkspaceState) -> None:
    if test.active_operation_id is not None:
        raise _operation_in_progress()
    question_set = state.question_set
    if question_set is None or question_set.status != QuestionSetStatus.DRAFT:
        raise AppError(
            status_code=409,
            code="question_set_not_editable",
            message="Generate a draft question set before asking AI for another question.",
        )
    if question_set.source != QuestionSetSource.PRODUCT_CONTEXT:
        raise AppError(
            status_code=409,
            code="question_set_not_editable",
            message="Generate a product-only question set before adding questions.",
        )
    if question_set.configuration_version != state.configuration.version:
        raise AppError(
            status_code=409,
            code="question_set_stale",
            message="Generate a new set after the latest Product setup changes.",
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
        key = _normalized_question_key(text)
        if not key or key in normalized:
            raise ValueError("The generated questions are not unique.")
        normalized.add(key)
        question_texts.append(text)
    return question_texts


def _validate_reviewed_questions(
    question_set: QuestionSet,
    submitted_items: list[ConfirmQuestionItem],
) -> list[Question]:
    """Build a reviewed set without changing the persisted draft on invalid input."""

    if not 1 <= len(submitted_items) <= 15:
        raise _question_review_error(
            "Submit between 1 and 15 questions.",
            field_errors={"items": ["Submit between 1 and 15 questions."]},
        )

    original_by_id = {question.id: question for question in question_set.items}
    seen_ids: set[str] = set()
    seen_texts: set[str] = set()
    reviewed: list[Question] = []

    for index, submitted in enumerate(submitted_items):
        field_prefix = f"items.{index}"
        question_id = submitted.id
        if question_id is not None:
            if question_id not in original_by_id:
                raise _question_review_error(
                    "The reviewed questions contain an unknown question.",
                    field_errors={
                        f"{field_prefix}.id": ["This question is not in the current draft."]
                    },
                )
            if question_id in seen_ids:
                raise _question_review_error(
                    "Each generated question must appear exactly once.",
                    field_errors={f"{field_prefix}.id": ["This question appears more than once."]},
                )
            seen_ids.add(question_id)

        text = submitted.text.strip()
        if not text:
            raise _question_review_error(
                "Question text must not be blank.",
                field_errors={f"{field_prefix}.text": ["Enter a question."]},
            )
        text_key = _normalized_question_key(text)
        if not text_key or text_key in seen_texts:
            raise _question_review_error(
                "Questions must be unique.",
                field_errors={f"{field_prefix}.text": ["Enter a unique question."]},
            )
        seen_texts.add(text_key)
        reviewed.append(Question(id=question_id or str(uuid4()), text=text))

    missing_ids = set(original_by_id) - seen_ids
    if missing_ids:
        raise _question_review_error(
            "Every generated question must remain in the reviewed set.",
            field_errors={"items": ["Keep every generated question before confirming."]},
        )
    return reviewed


def _normalized_question_key(text: str) -> str:
    return " ".join(
        part for part in re.split(r"[^\w]+", unicodedata.normalize("NFKC", text).casefold()) if part
    )


def _question_review_error(
    message: str,
    *,
    field_errors: dict[str, list[str]],
) -> AppError:
    return AppError(
        status_code=422,
        code="question_review_invalid",
        message=message,
        field_errors=field_errors,
    )


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
