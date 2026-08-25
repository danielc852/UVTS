import asyncio
import logging
import random
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from uvts_api.adapters.db.models import Document, QuestionEvaluationRecord, TestRun
from uvts_api.agents.errors import EvaluatorRateLimitError, describe_evaluator_failure
from uvts_api.agents.evaluator import EvaluatorAgent
from uvts_api.agents.schemas import QuestionEvaluationOutput
from uvts_api.core.errors import AppError
from uvts_api.domain.enums import TestStatus
from uvts_api.ports.notifications import StateNotifications
from uvts_api.ports.question_generator import AgentProductImage
from uvts_api.ports.storage import DocumentStorage
from uvts_api.schemas.workspace import (
    CoverageStatus,
    EvaluationItem,
    EvaluationSource,
    EvaluationStatus,
    Evidence,
    ManualStatus,
    Question,
    QuestionResult,
    QuestionSetStatus,
    Report,
    WorkflowStage,
    WorkspaceError,
    WorkspaceState,
)
from uvts_api.services.events import publish_test_change
from uvts_api.services.question_generation import build_question_generation_input
from uvts_api.services.reporting import FAILED_INFORMATION_NEEDED as FAILED_INFORMATION_NEEDED
from uvts_api.services.reporting import (
    build_coverage_counts,
    build_incomplete_report,
    build_question_results,
    build_report,
    build_report_synthesis_error,
)
from uvts_api.services.tests import lock_test
from uvts_api.services.workspace import load_workspace_state, update_state

logger = logging.getLogger(__name__)

QUESTION_FAILURE_MESSAGE = "The question could not be checked. Try this question again."
_RATE_LIMIT_MAX_RETRIES = 2
_RATE_LIMIT_BACKOFF_BASE_SECONDS = 1.0
_RATE_LIMIT_JITTER_SECONDS = 0.25


@dataclass(frozen=True, slots=True)
class _EvaluationOutcome:
    question: Question
    output: QuestionEvaluationOutput | None = None
    error: Exception | None = None


class _RateLimitCooldown:
    """Share a provider-requested pause across one evaluation operation."""

    def __init__(self) -> None:
        self._resume_at = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        while True:
            async with self._lock:
                delay = self._resume_at - asyncio.get_running_loop().time()
            if delay <= 0:
                return
            await asyncio.sleep(delay)

    async def postpone(self, delay: float) -> None:
        async with self._lock:
            resume_at = asyncio.get_running_loop().time() + delay
            self._resume_at = max(self._resume_at, resume_at)


async def start_evaluation(
    *,
    db: AsyncSession,
    test: TestRun,
    agent_settings: Mapping[str, object],
) -> tuple[str, list[str]]:
    test = await lock_test(db, test.id)
    state = await load_workspace_state(db, test)
    if test.active_operation_id is not None:
        raise _operation_in_progress()
    if state.manual_upload is not None:
        raise AppError(
            status_code=409,
            code="manual_upload_in_progress",
            message="Wait for the current PDF check to finish before evaluating questions.",
            retryable=True,
        )
    if (
        state.question_set is None
        or state.question_set.status != QuestionSetStatus.CONFIRMED
        or not state.questions
    ):
        raise AppError(
            status_code=409,
            code="evaluation_not_ready",
            message="Generate and review the questions before starting the evaluation.",
        )
    manual = await db.scalar(
        select(Document).where(
            Document.test_run_id == test.id,
            Document.role == "active",
            Document.status == "ready",
        )
    )
    if (
        manual is None
        or not manual.pages
        or state.manual is None
        or state.manual.status != ManualStatus.READY
        or state.manual.id != manual.id
    ):
        raise AppError(
            status_code=409,
            code="manual_not_ready",
            message="Wait for the manual to be ready before starting the evaluation.",
        )

    operation_id = str(uuid4())
    source = EvaluationSource(
        question_set_id=state.question_set.id,
        manual_id=manual.id,
    )
    question_ids = [question.id for question in state.questions]
    await db.execute(
        delete(QuestionEvaluationRecord).where(QuestionEvaluationRecord.test_run_id == test.id)
    )
    db.add_all(
        [
            QuestionEvaluationRecord(
                test_run_id=test.id,
                question_id=question_id,
                question_set_id=source.question_set_id,
                manual_id=source.manual_id,
                status=EvaluationStatus.WAITING.value,
            )
            for question_id in question_ids
        ]
    )
    test.active_operation_id = operation_id
    recorded_settings = dict(test.agent_settings)
    recorded_settings["evaluator"] = dict(agent_settings)
    test.agent_settings = recorded_settings
    test.status = TestStatus.EVALUATING.value
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": WorkflowStage.EVALUATION,
                "evaluation_source": source,
                "evaluation": [
                    EvaluationItem(question_id=question_id, status=EvaluationStatus.WAITING)
                    for question_id in question_ids
                ],
                "report": None,
                "error": None,
            }
        ),
    )
    await db.commit()
    return operation_id, question_ids


async def start_question_retry(
    *,
    db: AsyncSession,
    test: TestRun,
    question_id: str,
) -> tuple[str, list[str]]:
    test = await lock_test(db, test.id)
    state = await load_workspace_state(db, test)
    _ensure_no_active_operation(test)
    _ensure_current_evaluation_source(state)
    if question_id not in {question.id for question in state.questions}:
        raise AppError(
            status_code=404,
            code="question_not_found",
            message="This question was not found in the test.",
        )
    record = await _record_for_question(db, state, test.id, question_id)
    if record is None:
        raise AppError(
            status_code=404,
            code="question_not_found",
            message="This question was not found in the evaluation.",
        )
    if record.status != EvaluationStatus.FAILED:
        raise AppError(
            status_code=409,
            code="question_retry_not_available",
            message="Only a failed question can be tried again.",
        )
    operation_id = await _prepare_retry(
        db=db,
        test=test,
        state=state,
        records=[record],
    )
    return operation_id, [question_id]


async def start_failed_retries(
    *,
    db: AsyncSession,
    test: TestRun,
) -> tuple[str, list[str]]:
    test = await lock_test(db, test.id)
    state = await load_workspace_state(db, test)
    _ensure_no_active_operation(test)
    source = _ensure_current_evaluation_source(state)
    records_by_id = {
        record.question_id: record
        for record in (
            await db.scalars(
                select(QuestionEvaluationRecord).where(
                    QuestionEvaluationRecord.test_run_id == test.id,
                    QuestionEvaluationRecord.question_set_id == source.question_set_id,
                    QuestionEvaluationRecord.manual_id == source.manual_id,
                    QuestionEvaluationRecord.status == EvaluationStatus.FAILED.value,
                )
            )
        ).all()
    }
    failed_records = [
        records_by_id[question.id] for question in state.questions if question.id in records_by_id
    ]
    if not failed_records:
        raise AppError(
            status_code=409,
            code="no_failed_questions",
            message="There are no failed questions to try again.",
        )
    operation_id = await _prepare_retry(
        db=db,
        test=test,
        state=state,
        records=failed_records,
    )
    return operation_id, [record.question_id for record in failed_records]


async def start_report_retry(
    *,
    db: AsyncSession,
    test: TestRun,
) -> tuple[str, list[str]]:
    test = await lock_test(db, test.id)
    state = await load_workspace_state(db, test)
    _ensure_no_active_operation(test)
    _ensure_current_evaluation_source(state)
    if state.report is None or state.error is None or state.error.code != "report_synthesis_failed":
        raise AppError(
            status_code=409,
            code="report_retry_not_available",
            message="This report does not need to be finished again.",
        )
    operation_id = str(uuid4())
    test.active_operation_id = operation_id
    test.status = TestStatus.EVALUATING.value
    update_state(test, state.model_copy(update={"error": None}))
    await db.commit()
    return operation_id, []


async def process_evaluation_operation(
    *,
    db: AsyncSession,
    storage: DocumentStorage,
    agent: EvaluatorAgent,
    notifications: StateNotifications,
    test_id: str,
    operation_id: str,
    question_ids: Sequence[str],
    max_concurrency: int = 4,
) -> None:
    try:
        context = await _operation_context(db, storage, test_id, operation_id)
    except Exception as error:
        await fail_evaluation_dispatch(
            db=db,
            notifications=notifications,
            test_id=test_id,
            operation_id=operation_id,
            question_ids=question_ids,
            error=error,
        )
        return
    if context is None:
        return
    questions, manual_pages, product_image, product_description = context
    questions_by_id = {question.id: question for question in questions}
    waiting = deque(
        question
        for question_id in question_ids
        if (question := questions_by_id.get(question_id)) is not None
    )
    active: dict[asyncio.Task[_EvaluationOutcome], Question] = {}
    cooldown = _RateLimitCooldown()

    while waiting or active:
        while waiting and len(active) < max_concurrency:
            question = waiting.popleft()
            if not await _mark_question_checking(
                db=db,
                notifications=notifications,
                test_id=test_id,
                operation_id=operation_id,
                question_id=question.id,
            ):
                await _cancel_evaluations(active)
                return
            task = asyncio.create_task(
                _evaluate_question_with_rate_limit_retries(
                    agent=agent,
                    question=question,
                    manual_pages=manual_pages,
                    product_image=product_image,
                    product_description=product_description,
                    cooldown=cooldown,
                    test_id=test_id,
                    operation_id=operation_id,
                )
            )
            active[task] = question

        done, _ = await asyncio.wait(active, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            question = active.pop(task)
            outcome = task.result()
            if outcome.error is not None:
                _log_question_failure(
                    outcome.error,
                    test_id=test_id,
                    operation_id=operation_id,
                    question_id=question.id,
                )
                persisted = await _mark_question_failed(
                    db=db,
                    notifications=notifications,
                    test_id=test_id,
                    operation_id=operation_id,
                    question_id=question.id,
                )
            else:
                assert outcome.output is not None
                persisted = await _mark_question_complete(
                    db=db,
                    notifications=notifications,
                    test_id=test_id,
                    operation_id=operation_id,
                    question=question,
                    output=outcome.output,
                )
            if not persisted:
                await _cancel_evaluations(active)
                return

    await _finalize_report(
        db=db,
        agent=agent,
        notifications=notifications,
        test_id=test_id,
        operation_id=operation_id,
    )


async def _evaluate_question_with_rate_limit_retries(
    *,
    agent: EvaluatorAgent,
    question: Question,
    manual_pages: Sequence[Mapping[str, object]],
    product_image: AgentProductImage | None,
    product_description: str,
    cooldown: _RateLimitCooldown,
    test_id: str,
    operation_id: str,
) -> _EvaluationOutcome:
    for retry_attempt in range(_RATE_LIMIT_MAX_RETRIES + 1):
        await cooldown.wait()
        try:
            output = await agent.evaluate_question(
                question=question,
                manual_pages=manual_pages,
                product_image=product_image,
                product_description=product_description,
            )
            return _EvaluationOutcome(question=question, output=output)
        except EvaluatorRateLimitError as error:
            if retry_attempt >= _RATE_LIMIT_MAX_RETRIES:
                return _EvaluationOutcome(question=question, error=error)
            delay = error.retry_after_seconds
            if delay is None:
                delay = (
                    _RATE_LIMIT_BACKOFF_BASE_SECONDS * (2**retry_attempt)
                    + random.uniform(0.0, _RATE_LIMIT_JITTER_SECONDS)
                )
            await cooldown.postpone(delay)
            logger.warning(
                "Question evaluation rate limited; retry scheduled",
                extra={
                    "test_id": test_id,
                    "operation_id": operation_id,
                    "question_id": question.id,
                    "retry_attempt": retry_attempt + 1,
                    "retry_delay_seconds": round(delay, 3),
                },
            )
        except Exception as error:
            return _EvaluationOutcome(question=question, error=error)
    raise AssertionError("rate-limit retry loop exhausted without an outcome")


async def _cancel_evaluations(
    active: Mapping[asyncio.Task[_EvaluationOutcome], Question],
) -> None:
    tasks = list(active)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def _log_question_failure(
    error: Exception,
    *,
    test_id: str,
    operation_id: str,
    question_id: str,
) -> None:
    failure = describe_evaluator_failure(error)
    logger.warning(
        "Question evaluation failed",
        extra={
            "test_id": test_id,
            "operation_id": operation_id,
            "question_id": question_id,
            "error_stage": failure.stage.value,
            "error_type": failure.error_type,
            "error_message": failure.message,
        },
        exc_info=(type(error), error, error.__traceback__),
    )


async def publish_evaluation_change(
    notifications: StateNotifications,
    test_id: str,
) -> None:
    await publish_test_change(
        notifications,
        test_id,
        logger=logger,
        failure_message="Evaluation state notification failed",
    )


async def fail_evaluation_dispatch(
    *,
    db: AsyncSession,
    notifications: StateNotifications,
    test_id: str,
    operation_id: str,
    question_ids: Sequence[str],
    error: Exception,
) -> None:
    await db.rollback()
    test = await db.get(TestRun, test_id)
    if test is None:
        return
    await db.refresh(test)
    if test.active_operation_id != operation_id:
        return
    state = await load_workspace_state(db, test)
    source = _ensure_current_evaluation_source(state)
    report: Report | None
    if question_ids:
        retry_ids = set(question_ids)
        records = list(
            (
                await db.scalars(
                    select(QuestionEvaluationRecord).where(
                        QuestionEvaluationRecord.test_run_id == test_id,
                        QuestionEvaluationRecord.question_set_id == source.question_set_id,
                        QuestionEvaluationRecord.manual_id == source.manual_id,
                    )
                )
            ).all()
        )
        for record in records:
            if record.question_id in retry_ids:
                record.status = EvaluationStatus.FAILED.value
                record.result = None
                record.error = QUESTION_FAILURE_MESSAGE
        evaluation = [
            item.model_copy(
                update={
                    "status": EvaluationStatus.FAILED,
                    "error": QUESTION_FAILURE_MESSAGE,
                }
            )
            if item.question_id in retry_ids
            else item
            for item in state.evaluation
        ]
        results = build_question_results(state.questions, records)
        counts = build_coverage_counts(results)
        report = build_incomplete_report(state.evaluation_source, results, counts)
        workspace_error = WorkspaceError(
            code="evaluation_dispatch_failed",
            title="The evaluation could not start",
            message=(
                "The questions were saved, but UVTS could not start checking them. Try again."
            ),
            stage=WorkflowStage.EVALUATION,
            retryable=True,
        )
    else:
        evaluation = state.evaluation
        report = state.report
        workspace_error = build_report_synthesis_error()
    test.active_operation_id = None
    test.status = TestStatus.INCOMPLETE.value
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": WorkflowStage.REPORT,
                "evaluation": evaluation,
                "report": report,
                "error": workspace_error,
            }
        ),
    )
    await db.commit()
    logger.warning(
        "Evaluation job dispatch failed",
        extra={
            "test_id": test_id,
            "operation_id": operation_id,
            "error_type": type(error).__name__,
        },
    )
    await publish_evaluation_change(notifications, test_id)


async def _prepare_retry(
    *,
    db: AsyncSession,
    test: TestRun,
    state: WorkspaceState,
    records: Sequence[QuestionEvaluationRecord],
) -> str:
    operation_id = str(uuid4())
    retry_ids = {record.question_id for record in records}
    for record in records:
        record.status = EvaluationStatus.WAITING.value
        record.result = None
        record.error = None
    test.active_operation_id = operation_id
    test.status = TestStatus.EVALUATING.value
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": WorkflowStage.EVALUATION,
                "evaluation": [
                    item.model_copy(update={"status": EvaluationStatus.WAITING, "error": None})
                    if item.question_id in retry_ids
                    else item
                    for item in state.evaluation
                ],
                "report": None,
                "error": None,
            }
        ),
    )
    await db.commit()
    return operation_id


async def _operation_context(
    db: AsyncSession,
    storage: DocumentStorage,
    test_id: str,
    operation_id: str,
) -> tuple[list[Question], list[dict[str, object]], AgentProductImage | None, str] | None:
    test = await _active_test(db, test_id, operation_id)
    if test is None:
        return None
    state = await load_workspace_state(db, test)
    source = _ensure_current_evaluation_source(state)
    question_set = state.question_set
    assert question_set is not None
    document = await db.scalar(
        select(Document).where(
            Document.test_run_id == test_id,
            Document.id == source.manual_id,
            Document.role == "active",
            Document.status == "ready",
        )
    )
    if document is None:
        raise AppError(
            status_code=409,
            code="evaluation_manual_unavailable",
            message="The manual selected for this evaluation is no longer available.",
        )
    try:
        product_context = await build_question_generation_input(db=db, storage=storage, test=test)
        product_image: AgentProductImage | None = product_context.product_image
        product_description = product_context.product_description
    except AppError:
        if question_set.source.value != "legacy_manual_unknown":
            raise
        product_image = None
        product_description = state.configuration.product_description
    return (
        question_set.items,
        list(document.pages),
        product_image,
        product_description,
    )


async def _active_test(
    db: AsyncSession,
    test_id: str,
    operation_id: str,
) -> TestRun | None:
    test = await db.get(TestRun, test_id)
    if test is None:
        return None
    await db.refresh(test)
    if test.active_operation_id != operation_id:
        return None
    state = await load_workspace_state(db, test)
    if state.current_stage not in {WorkflowStage.EVALUATION, WorkflowStage.REPORT}:
        return None
    return test


async def _record_for_question(
    db: AsyncSession,
    state: WorkspaceState,
    test_id: str,
    question_id: str,
) -> QuestionEvaluationRecord | None:
    source = state.evaluation_source
    if source is None:
        return None
    return cast(
        QuestionEvaluationRecord | None,
        await db.scalar(
            select(QuestionEvaluationRecord).where(
                QuestionEvaluationRecord.test_run_id == test_id,
                QuestionEvaluationRecord.question_id == question_id,
                QuestionEvaluationRecord.question_set_id == source.question_set_id,
                QuestionEvaluationRecord.manual_id == source.manual_id,
            )
        ),
    )


async def _mark_question_checking(
    *,
    db: AsyncSession,
    notifications: StateNotifications,
    test_id: str,
    operation_id: str,
    question_id: str,
) -> bool:
    active = await _active_record(db, test_id, operation_id, question_id)
    if active is None:
        return False
    test, record = active
    if record is None:
        return True
    record.status = EvaluationStatus.CHECKING.value
    record.error = None
    record.attempt += 1
    await _commit_evaluation_item(
        db=db,
        notifications=notifications,
        test=test,
        question_id=question_id,
        status=EvaluationStatus.CHECKING,
        error=None,
    )
    return True


async def _mark_question_failed(
    *,
    db: AsyncSession,
    notifications: StateNotifications,
    test_id: str,
    operation_id: str,
    question_id: str,
) -> bool:
    active = await _active_record(db, test_id, operation_id, question_id)
    if active is None:
        return False
    test, record = active
    if record is None:
        return True
    record.status = EvaluationStatus.FAILED.value
    record.result = None
    record.error = QUESTION_FAILURE_MESSAGE
    await _commit_evaluation_item(
        db=db,
        notifications=notifications,
        test=test,
        question_id=question_id,
        status=EvaluationStatus.FAILED,
        error=QUESTION_FAILURE_MESSAGE,
    )
    return True


async def _mark_question_complete(
    *,
    db: AsyncSession,
    notifications: StateNotifications,
    test_id: str,
    operation_id: str,
    question: Question,
    output: QuestionEvaluationOutput,
) -> bool:
    active = await _active_record(db, test_id, operation_id, question.id)
    if active is None:
        return False
    test, record = active
    if record is None:
        return True
    result = QuestionResult(
        question=question,
        status=CoverageStatus(output.status),
        information_needed=output.information_needed,
        information_found=output.information_found,
        information_missing=output.information_missing,
        evidence=[Evidence(page=item.page, extract=item.extract) for item in output.evidence],
    )
    record.status = EvaluationStatus.COMPLETE.value
    record.result = result.model_dump(mode="json", by_alias=True)
    record.error = None
    await _commit_evaluation_item(
        db=db,
        notifications=notifications,
        test=test,
        question_id=question.id,
        status=EvaluationStatus.COMPLETE,
        error=None,
    )
    return True


async def _active_record(
    db: AsyncSession,
    test_id: str,
    operation_id: str,
    question_id: str,
) -> tuple[TestRun, QuestionEvaluationRecord | None] | None:
    test = await _active_test(db, test_id, operation_id)
    if test is None:
        return None
    state = await load_workspace_state(db, test)
    record = await _record_for_question(db, state, test_id, question_id)
    return test, record


async def _commit_evaluation_item(
    *,
    db: AsyncSession,
    notifications: StateNotifications,
    test: TestRun,
    question_id: str,
    status: EvaluationStatus,
    error: str | None,
) -> None:
    await _update_evaluation_item(
        db,
        test,
        question_id=question_id,
        status=status,
        error=error,
    )
    await db.commit()
    await publish_evaluation_change(notifications, test.id)


async def _update_evaluation_item(
    db: AsyncSession,
    test: TestRun,
    *,
    question_id: str,
    status: EvaluationStatus,
    error: str | None,
) -> None:
    state = await load_workspace_state(db, test)
    update_state(
        test,
        state.model_copy(
            update={
                "evaluation": [
                    item.model_copy(update={"status": status, "error": error})
                    if item.question_id == question_id
                    else item
                    for item in state.evaluation
                ]
            }
        ),
    )


async def _finalize_report(
    *,
    db: AsyncSession,
    agent: EvaluatorAgent,
    notifications: StateNotifications,
    test_id: str,
    operation_id: str,
) -> None:
    test = await _active_test(db, test_id, operation_id)
    if test is None:
        return
    state = await load_workspace_state(db, test)
    source = _ensure_current_evaluation_source(state)
    records = list(
        (
            await db.scalars(
                select(QuestionEvaluationRecord).where(
                    QuestionEvaluationRecord.test_run_id == test_id,
                    QuestionEvaluationRecord.question_set_id == source.question_set_id,
                    QuestionEvaluationRecord.manual_id == source.manual_id,
                )
            )
        ).all()
    )
    results = build_question_results(state.questions, records)
    counts = build_coverage_counts(results)
    completed_results = [result for result in results if result.status != CoverageStatus.FAILED]

    try:
        synthesis = await agent.synthesize_report(
            results=completed_results,
        )
    except Exception as exc:
        failure = describe_evaluator_failure(exc)
        logger.warning(
            "Report synthesis failed",
            extra={
                "test_id": test_id,
                "operation_id": operation_id,
                "error_stage": failure.stage.value,
                "error_type": failure.error_type,
                "error_message": failure.message,
            },
            exc_info=True,
        )
        test = await _active_test(db, test_id, operation_id)
        if test is None:
            return
        state = await load_workspace_state(db, test)
        test.active_operation_id = None
        test.status = TestStatus.INCOMPLETE.value
        update_state(
            test,
            state.model_copy(
                update={
                    "current_stage": WorkflowStage.REPORT,
                    "report": build_incomplete_report(
                        state.evaluation_source,
                        results,
                        counts,
                    ),
                    "error": build_report_synthesis_error(),
                }
            ),
        )
        await db.commit()
        await publish_evaluation_change(notifications, test_id)
        return

    test = await _active_test(db, test_id, operation_id)
    if test is None:
        return
    state = await load_workspace_state(db, test)
    if state.evaluation_source is None:
        return
    report = build_report(
        source=state.evaluation_source,
        results=results,
        counts=counts,
        synthesis=synthesis,
    )
    test.active_operation_id = None
    test.status = TestStatus.COMPLETE.value if report.is_complete else TestStatus.INCOMPLETE.value
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": WorkflowStage.REPORT,
                "report": report,
                "error": None,
            }
        ),
    )
    await db.commit()
    await publish_evaluation_change(notifications, test_id)


def _ensure_no_active_operation(test: TestRun) -> None:
    if test.active_operation_id is not None:
        raise _operation_in_progress()


def _ensure_current_evaluation_source(state: WorkspaceState) -> EvaluationSource:
    source = state.evaluation_source
    question_set = state.question_set
    if (
        source is None
        or question_set is None
        or question_set.status != QuestionSetStatus.CONFIRMED
        or source.question_set_id != question_set.id
        or state.manual is None
        or source.manual_id != state.manual.id
    ):
        raise AppError(
            status_code=409,
            code="evaluation_source_changed",
            message="The confirmed questions or manual changed. Start a new evaluation.",
        )
    return source


def _operation_in_progress() -> AppError:
    return AppError(
        status_code=409,
        code="agent_operation_in_progress",
        message="Wait for the current test work to finish before trying again.",
        retryable=True,
    )
