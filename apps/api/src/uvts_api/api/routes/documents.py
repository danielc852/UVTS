import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile
from sqlalchemy import select
from starlette.responses import FileResponse

from uvts_api.adapters.db.models import Document
from uvts_api.api.dependencies import (
    CurrentSession,
    DatabaseSession,
    DocumentStorageDependency,
    OperationDispatcherDependency,
)
from uvts_api.core.errors import AppError, manual_not_found
from uvts_api.schemas.errors import ErrorResponse
from uvts_api.schemas.tests import TestResponse
from uvts_api.services.documents import (
    begin_manual_replacement,
    publish_change,
    remove_manual,
)
from uvts_api.services.tests import get_owned_test, to_test_response

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
    operation_dispatcher: OperationDispatcherDependency,
    file: Annotated[UploadFile, File()],
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id, for_update=True)
    filename = safe_filename(file)
    temporary = await save_temporary_upload(file)
    try:
        document_id = await begin_manual_replacement(
            db=db,
            storage=storage,
            test=test,
            filename=filename,
            source=temporary,
        )
    finally:
        await asyncio.to_thread(temporary.unlink, missing_ok=True)
    await publish_change(request.app.state.notifications, test.id)
    await operation_dispatcher.process_document(document_id)
    await db.refresh(test)
    return await to_test_response(db, test)


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
    await remove_manual(db=db, storage=storage, test=test)
    await publish_change(request.app.state.notifications, test.id)
    await db.refresh(test)
    return await to_test_response(db, test)
