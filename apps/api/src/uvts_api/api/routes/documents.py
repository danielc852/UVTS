import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, File, Request, UploadFile
from sqlalchemy import delete, select
from starlette.responses import FileResponse

from uvts_api.adapters.db.models import Document, QuestionEvaluationRecord
from uvts_api.api.dependencies import (
    CurrentSession,
    DatabaseSession,
    DocumentStorageDependency,
    RuntimeSettings,
)
from uvts_api.core.errors import AppError, manual_not_found
from uvts_api.domain.enums import TestStatus
from uvts_api.schemas.errors import ErrorResponse
from uvts_api.schemas.tests import TestResponse
from uvts_api.schemas.workspace import (
    ManualUpload,
    ManualUploadStatus,
    QuestionSetStatus,
    WorkflowStage,
    WorkspaceState,
)
from uvts_api.services.documents import (
    delete_storage_after_commit,
    process_pending_document,
    publish_change,
    update_state,
)
from uvts_api.services.tests import get_owned_test, to_test_response
from uvts_api.workers.documents import enqueue_document_processing

router = APIRouter(prefix="/tests", tags=["documents"])


async def save_temporary_upload(upload: UploadFile) -> Path:
    path: Path | None = None
    try:
        try:
            with NamedTemporaryFile(
                prefix="uvts-upload-", suffix=".pdf", delete=False
            ) as destination:
                path = Path(destination.name)
                while chunk := await upload.read(1024 * 1024):
                    destination.write(chunk)
        finally:
            await upload.close()
    except Exception:
        if path is not None:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        raise
    assert path is not None
    header = await asyncio.to_thread(read_header, path)
    if b"%PDF-" not in header:
        await asyncio.to_thread(path.unlink, missing_ok=True)
        raise AppError(
            status_code=422,
            code="manual_not_pdf",
            message="Upload a PDF file.",
            field_errors={"file": ["Upload a PDF file."]},
        )
    return path


def read_header(path: Path) -> bytes:
    with path.open("rb") as source:
        return source.read(1024)


def safe_filename(upload: UploadFile) -> str:
    filename = Path(upload.filename or "manual.pdf").name.strip()
    return (filename or "manual.pdf")[:255]


async def dispatch_processing(
    *,
    request: Request,
    db: DatabaseSession,
    storage: DocumentStorageDependency,
    settings: RuntimeSettings,
    document_id: str,
) -> None:
    if settings.document_processing_eager:
        await process_pending_document(
            db=db,
            storage=storage,
            notifications=request.app.state.notifications,
            document_id=document_id,
        )
    else:
        enqueue_document_processing(document_id)


@router.put(
    "/{test_id}/manual",
    response_model=TestResponse,
    status_code=202,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def replace_manual(
    test_id: str,
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
    storage: DocumentStorageDependency,
    settings: RuntimeSettings,
    file: Annotated[UploadFile, File()],
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id, for_update=True)
    state = WorkspaceState.model_validate(test.state)
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

    filename = safe_filename(file)
    temporary = await save_temporary_upload(file)
    storage_key = f"{uuid4()}.pdf"
    try:
        await storage.put(storage_key, temporary)
    finally:
        await asyncio.to_thread(temporary.unlink, missing_ok=True)
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
    await publish_change(request.app.state.notifications, test.id)
    await dispatch_processing(
        request=request,
        db=db,
        storage=storage,
        settings=settings,
        document_id=document.id,
    )
    await db.refresh(test)
    return to_test_response(test)


@router.get(
    "/{test_id}/manual/content",
    response_class=FileResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def manual_content(
    test_id: str,
    current: CurrentSession,
    db: DatabaseSession,
    storage: DocumentStorageDependency,
) -> FileResponse:
    test = await get_owned_test(db, test_id, current.id)
    document = await db.scalar(
        select(Document).where(Document.test_run_id == test.id, Document.role == "active")
    )
    if document is None:
        raise manual_not_found()
    try:
        path = await storage.local_path(document.storage_key)
    except FileNotFoundError as exc:
        raise manual_not_found() from exc
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=document.filename,
        content_disposition_type="inline",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete(
    "/{test_id}/manual",
    response_model=TestResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def delete_manual(
    test_id: str,
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
    storage: DocumentStorageDependency,
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id, for_update=True)
    if test.active_operation_id is not None:
        raise AppError(
            status_code=409,
            code="operation_in_progress",
            message="Wait for the current test work to finish before deleting the manual.",
            retryable=True,
        )
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
        delete(QuestionEvaluationRecord).where(
            QuestionEvaluationRecord.test_run_id == test.id
        )
    )
    state = WorkspaceState.model_validate(test.state)
    questions_confirmed = (
        state.question_set is not None
        and state.question_set.status == QuestionSetStatus.CONFIRMED
    )
    update_state(
        test,
        state.model_copy(
            update={
                "current_stage": (
                    WorkflowStage.UPLOAD
                    if questions_confirmed
                    else WorkflowStage.CONFIGURATION
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
        TestStatus.QUESTIONS_CONFIRMED.value
        if questions_confirmed
        else TestStatus.DRAFT.value
    )
    test.active_operation_id = None
    settings = dict(test.agent_settings)
    settings.pop("evaluator", None)
    test.agent_settings = settings
    await db.commit()
    await publish_change(request.app.state.notifications, test.id)
    for storage_key in storage_keys:
        await delete_storage_after_commit(storage, storage_key)
    await db.refresh(test)
    return to_test_response(test)
