import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from uvts_api.adapters.db.models import Document, TestRun
from uvts_api.ports.notifications import StateNotifications
from uvts_api.ports.storage import DocumentStorage
from uvts_api.schemas.workspace import (
    ManualStatus,
    ManualSummary,
    ManualUpload,
    ManualUploadStatus,
    WorkflowStage,
    WorkspaceError,
    WorkspaceState,
)

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
    try:
        await notifications.publish(test_id)
    except Exception:
        logger.warning("Document state notification failed", exc_info=True)


def update_state(test: TestRun, state: WorkspaceState) -> None:
    test.state = state.model_dump(mode="json", by_alias=True)
    test.state_version += 1


async def process_pending_document(
    *,
    db: AsyncSession,
    storage: DocumentStorage,
    notifications: StateNotifications,
    document_id: str,
) -> None:
    document = await db.scalar(select(Document).where(Document.id == document_id))
    if document is None or document.role != "pending":
        return
    test = await db.get(TestRun, document.test_run_id)
    if test is None:
        return

    document.status = ManualUploadStatus.PROCESSING.value
    state = WorkspaceState.model_validate(test.state)
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

    await db.refresh(document)
    await db.refresh(test)
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

    document.role = "active"
    document.status = ManualStatus.READY.value
    document.page_count = processed.page_count
    document.pages = processed.pages
    state = WorkspaceState.model_validate(test.state)
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": WorkflowStage.CONFIGURATION,
                "manual": ManualSummary(
                    id=document.id,
                    filename=document.filename,
                    page_count=processed.page_count,
                    status=ManualStatus.READY,
                ),
                "manual_upload": None,
                "questions": [],
                "evaluation": [],
                "report": None,
                "error": None,
            }
        ),
    )
    await db.commit()
    await publish_change(notifications, test.id)
    if old_storage_key is not None:
        await storage.delete(old_storage_key)


async def fail_pending_document(
    *,
    db: AsyncSession,
    storage: DocumentStorage,
    notifications: StateNotifications,
    document_id: str,
    error: ManualValidationError,
) -> None:
    document = await db.scalar(select(Document).where(Document.id == document_id))
    if document is None:
        return
    test = await db.get(TestRun, document.test_run_id)
    if test is None:
        return
    storage_key = document.storage_key
    active = await db.scalar(
        select(Document).where(
            Document.test_run_id == test.id,
            Document.role == "active",
        )
    )
    state = WorkspaceState.model_validate(test.state)
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
    await storage.delete(storage_key)
    await publish_change(notifications, test.id)
