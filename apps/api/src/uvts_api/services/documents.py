import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from uvts_api.adapters.db.models import Document, QuestionEvaluationRecord, TestRun
from uvts_api.core.errors import AppError, manual_not_found
from uvts_api.domain.enums import TestStatus
from uvts_api.ports.notifications import StateNotifications
from uvts_api.ports.storage import DocumentStorage
from uvts_api.schemas.workspace import (
    ManualStatus,
    ManualSummary,
    ManualUpload,
    ManualUploadStatus,
    QuestionSetStatus,
    WorkflowStage,
    WorkspaceError,
)
from uvts_api.services.events import publish_test_change
from uvts_api.services.workspace import load_workspace_state, update_state

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProcessedPdf:
    page_count: int
    pages: list[dict[str, object]]


class ManualValidationError(Exception):
    def __init__(self, *, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def inspect_pdf(path: Path) -> ProcessedPdf:
    try:
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted:
            raise ManualValidationError(
                code="manual_password_protected",
                message=(
                    "This PDF is password-protected. Remove the password and upload it again."
                ),
            )
        page_count = len(reader.pages)
        if page_count < 1:
            raise ManualValidationError(
                code="manual_page_count",
                message="This PDF does not contain any pages. Upload a PDF with 1–20 pages.",
            )
        if page_count > 20:
            raise ManualValidationError(
                code="manual_page_limit",
                message=(
                    f"This PDF has {page_count} pages. UVTS currently supports up to 20 pages."
                ),
            )

        pages: list[dict[str, object]] = []
        for page_number, page in enumerate(reader.pages, start=1):
            pages.append({"page": page_number, "text": page.extract_text() or ""})
        if not any(str(page["text"]).strip() for page in pages):
            raise ManualValidationError(
                code="manual_no_readable_text",
                message=(
                    "UVTS could not read the text in this PDF. "
                    "Scanned documents are not supported yet."
                ),
            )
        return ProcessedPdf(page_count=page_count, pages=pages)
    except ManualValidationError:
        raise
    except Exception as exc:
        raise ManualValidationError(
            code="manual_processing_failed",
            message="UVTS could not check this PDF. Try uploading it again.",
            retryable=True,
        ) from exc


async def publish_change(notifications: StateNotifications, test_id: str) -> None:
    await publish_test_change(
        notifications,
        test_id,
        logger=logger,
        failure_message="Document state notification failed",
    )


async def delete_storage_after_commit(storage: DocumentStorage, storage_key: str) -> None:
    """Best-effort cleanup that never invalidates an already committed transition."""

    for attempt in range(2):
        try:
            await storage.delete(storage_key)
            return
        except Exception:
            if attempt == 1:
                logger.warning(
                    "Committed document cleanup failed",
                    extra={"storage_key": storage_key},
                    exc_info=True,
                )


async def process_pending_document(
    *,
    db: AsyncSession,
    storage: DocumentStorage,
    notifications: StateNotifications,
    document_id: str,
) -> None:
    locked = await _lock_pending_document(db, document_id)
    if locked is None:
        return
    test, document = locked

    document.status = ManualUploadStatus.PROCESSING.value
    state = await load_workspace_state(db, test)
    update_state(
        test,
        state.model_copy(
            update={
                "manual_upload": ManualUpload(
                    id=document.id,
                    filename=document.filename,
                    status=ManualUploadStatus.PROCESSING,
                ),
                "error": None,
            }
        ),
    )
    await db.commit()
    await publish_change(notifications, test.id)

    try:
        storage_path = await storage.local_path(document.storage_key)
        processed = await asyncio.to_thread(inspect_pdf, storage_path)
    except ManualValidationError as error:
        await fail_pending_document(
            db=db,
            storage=storage,
            notifications=notifications,
            document_id=document.id,
            error=error,
        )
        return
    except Exception:
        await fail_pending_document(
            db=db,
            storage=storage,
            notifications=notifications,
            document_id=document.id,
            error=ManualValidationError(
                code="manual_processing_failed",
                message="UVTS could not check this PDF. Try uploading it again.",
                retryable=True,
            ),
        )
        return

    try:
        promoted = await promote_pending_document(
            db=db,
            document_id=document_id,
            processed=processed,
        )
    except Exception:
        await db.rollback()
        await fail_pending_document(
            db=db,
            storage=storage,
            notifications=notifications,
            document_id=document_id,
            error=ManualValidationError(
                code="manual_processing_failed",
                message="UVTS could not finish adding this PDF. Try uploading it again.",
                retryable=True,
            ),
        )
        return
    if promoted is None:
        return
    test_id, old_storage_key = promoted
    await publish_change(notifications, test_id)
    if old_storage_key is not None:
        await delete_storage_after_commit(storage, old_storage_key)


async def begin_manual_replacement(
    *,
    db: AsyncSession,
    storage: DocumentStorage,
    test: TestRun,
    filename: str,
    source: Path,
) -> str:
    """Persist a staged upload and record it as the pending manual."""

    state = await load_workspace_state(db, test)
    if state.question_set is None or state.question_set.status != QuestionSetStatus.CONFIRMED:
        raise AppError(
            status_code=409,
            code="manual_locked",
            message="Confirm the question set before uploading a manual.",
        )
    if test.active_operation_id is not None:
        raise AppError(
            status_code=409,
            code="operation_in_progress",
            message="Wait for the current test work to finish before replacing the manual.",
            retryable=True,
        )
    pending = await db.scalar(
        select(Document).where(Document.test_run_id == test.id, Document.role == "pending")
    )
    if pending is not None:
        raise AppError(
            status_code=409,
            code="manual_upload_in_progress",
            message="Wait for the current PDF check to finish before uploading another manual.",
            retryable=True,
        )

    storage_key = f"{uuid4()}.pdf"
    await storage.put(storage_key, source)
    try:
        document = Document(
            test_run_id=test.id,
            role="pending",
            filename=filename,
            storage_key=storage_key,
            status=ManualUploadStatus.CHECKING.value,
        )
        db.add(document)
        await db.flush()
        update_state(
            test,
            state.model_copy(
                update={
                    "manual_upload": ManualUpload(
                        id=document.id,
                        filename=document.filename,
                        status=ManualUploadStatus.CHECKING,
                    ),
                    "error": None,
                }
            ),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        await delete_storage_after_commit(storage, storage_key)
        raise
    return document.id


async def remove_manual(
    *,
    db: AsyncSession,
    storage: DocumentStorage,
    test: TestRun,
) -> None:
    """Remove manual records and reset all state derived from the manual."""

    if test.active_operation_id is not None:
        raise AppError(
            status_code=409,
            code="operation_in_progress",
            message="Wait for the current test work to finish before deleting the manual.",
            retryable=True,
        )
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
    if not documents:
        raise manual_not_found()
    storage_keys = [document.storage_key for document in documents]
    for document in documents:
        await db.delete(document)
    await db.execute(
        delete(QuestionEvaluationRecord).where(QuestionEvaluationRecord.test_run_id == test.id)
    )
    questions_confirmed = (
        state.question_set is not None
        and state.question_set.status == QuestionSetStatus.CONFIRMED
    )
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": (
                    WorkflowStage.UPLOAD if questions_confirmed else WorkflowStage.CONFIGURATION
                ),
                "manual": None,
                "manual_upload": None,
                "evaluation_source": None,
                "evaluation": [],
                "report": None,
                "error": None,
            }
        ),
    )
    test.status = (
        TestStatus.QUESTIONS_CONFIRMED.value if questions_confirmed else TestStatus.DRAFT.value
    )
    test.active_operation_id = None
    settings = dict(test.agent_settings)
    settings.pop("evaluator", None)
    test.agent_settings = settings
    await db.commit()
    for storage_key in storage_keys:
        await delete_storage_after_commit(storage, storage_key)


async def promote_pending_document(
    *,
    db: AsyncSession,
    document_id: str,
    processed: ProcessedPdf,
) -> tuple[str, str | None] | None:
    """Atomically replace the active manual only after the candidate is valid."""

    locked = await _lock_pending_document(db, document_id)
    if locked is None:
        return None
    test, document = locked
    state = await load_workspace_state(db, test)
    active = await db.scalar(
        select(Document).where(
            Document.test_run_id == test.id,
            Document.role == "active",
        )
    )
    old_storage_key = active.storage_key if active is not None else None
    if active is not None:
        await db.delete(active)
        await db.flush()

    await db.execute(
        delete(QuestionEvaluationRecord).where(QuestionEvaluationRecord.test_run_id == test.id)
    )

    document.role = "active"
    document.status = ManualStatus.READY.value
    document.page_count = processed.page_count
    document.pages = processed.pages
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": WorkflowStage.EVALUATION,
                "manual": ManualSummary(
                    id=document.id,
                    filename=document.filename,
                    page_count=processed.page_count,
                    status=ManualStatus.READY,
                ),
                "manual_upload": None,
                "evaluation_source": None,
                "evaluation": [],
                "report": None,
                "error": None,
            }
        ),
    )
    test.status = TestStatus.READY.value
    settings = dict(test.agent_settings)
    settings.pop("evaluator", None)
    test.agent_settings = settings
    await db.commit()
    return test.id, old_storage_key


async def fail_pending_document(
    *,
    db: AsyncSession,
    storage: DocumentStorage,
    notifications: StateNotifications,
    document_id: str,
    error: ManualValidationError,
) -> None:
    locked = await _lock_pending_document(db, document_id)
    if locked is None:
        return
    test, document = locked
    storage_key = document.storage_key
    active = await db.scalar(
        select(Document).where(
            Document.test_run_id == test.id,
            Document.role == "active",
        )
    )
    state = await load_workspace_state(db, test)
    await db.delete(document)
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": (
                    state.current_stage if active is not None else WorkflowStage.UPLOAD
                ),
                "manual_upload": None,
                "error": WorkspaceError(
                    code=error.code,
                    title="The manual was not added",
                    message=error.message,
                    stage=WorkflowStage.UPLOAD,
                    retryable=error.retryable,
                ),
            }
        ),
    )
    await db.commit()
    await delete_storage_after_commit(storage, storage_key)
    await publish_change(notifications, test.id)


async def _lock_pending_document(
    db: AsyncSession,
    document_id: str,
) -> tuple[TestRun, Document] | None:
    candidate = await db.scalar(select(Document).where(Document.id == document_id))
    if candidate is None or candidate.role != "pending":
        return None
    test = await db.scalar(
        select(TestRun)
        .where(TestRun.id == candidate.test_run_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if test is None:
        return None
    document = await db.scalar(
        select(Document)
        .where(
            Document.id == document_id,
            Document.test_run_id == test.id,
            Document.role == "pending",
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if document is None:
        return None
    return test, document
