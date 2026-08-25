import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile

from uvts_api.adapters.db.models import TestRun
from uvts_api.api.dependencies import CurrentSession, DatabaseSession, DocumentStorageDependency
from uvts_api.core.errors import AppError
from uvts_api.schemas.errors import ErrorResponse
from uvts_api.schemas.tests import TestResponse
from uvts_api.services.configuration import (
    ProductImageUpload,
    persist_configuration,
)
from uvts_api.services.documents import publish_change
from uvts_api.services.tests import get_owned_test, to_test_response
from uvts_api.services.workspace import new_workspace_state

router = APIRouter(prefix="/tests", tags=["configuration"])

MAX_PRODUCT_IMAGE_BYTES = 10 * 1024 * 1024


async def save_temporary_image(upload: UploadFile) -> tuple[Path, int]:
    content_type = upload.content_type or ""
    if not content_type.startswith("image/"):
        await upload.close()
        raise AppError(
            status_code=422,
            code="product_image_type",
            message="Upload an image file.",
            field_errors={"productImage": ["Upload an image file."]},
        )

    with NamedTemporaryFile(prefix="uvts-product-image-", delete=False) as destination:
        path = Path(destination.name)
        size = 0
        try:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_PRODUCT_IMAGE_BYTES:
                    raise AppError(
                        status_code=422,
                        code="product_image_too_large",
                        message="Upload an image smaller than 10 MB.",
                        field_errors={
                            "productImage": ["Upload an image smaller than 10 MB."]
                        },
                    )
                destination.write(chunk)
        except Exception:
            await asyncio.to_thread(path.unlink, missing_ok=True)
            raise
        finally:
            await upload.close()

    if size == 0:
        await asyncio.to_thread(path.unlink, missing_ok=True)
        raise AppError(
            status_code=422,
            code="product_image_empty",
            message="The selected image is empty. Choose another image.",
            field_errors={
                "productImage": ["The selected image is empty. Choose another image."]
            },
        )
    return path, size


def safe_image_filename(upload: UploadFile) -> str:
    filename = Path(upload.filename or "product-image").name.strip()
    return (filename or "product-image")[:255]


async def prepare_product_image(upload: UploadFile | None) -> ProductImageUpload | None:
    if upload is None:
        return None
    filename = safe_image_filename(upload)
    content_type = upload.content_type or ""
    path, size_bytes = await save_temporary_image(upload)
    return ProductImageUpload(
        path=path,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
    )


@router.post(
    "",
    response_model=TestResponse,
    status_code=201,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def create_test_from_configuration(
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
    storage: DocumentStorageDependency,
    product_description: Annotated[str, Form(alias="productDescription")],
    total_questions: Annotated[int, Form(alias="totalQuestions", ge=1, le=15)],
    product_image: Annotated[UploadFile, File(alias="productImage")],
) -> TestResponse:
    prepared_image = await prepare_product_image(product_image)
    assert prepared_image is not None
    try:
        test = TestRun(
            owner_session_id=current.id,
            state=new_workspace_state(),
        )
        db.add(test)
        await db.flush()
        await persist_configuration(
            db=db,
            storage=storage,
            test=test,
            product_description=product_description,
            total_questions=total_questions,
            product_image=prepared_image,
            require_image=True,
        )
    finally:
        await asyncio.to_thread(prepared_image.path.unlink, missing_ok=True)
    await publish_change(request.app.state.notifications, test.id)
    await db.refresh(test)
    return await to_test_response(db, test)


@router.put(
    "/{test_id}/configuration",
    response_model=TestResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def save_configuration(
    test_id: str,
    request: Request,
    current: CurrentSession,
    db: DatabaseSession,
    storage: DocumentStorageDependency,
    product_description: Annotated[str, Form(alias="productDescription")],
    total_questions: Annotated[int, Form(alias="totalQuestions", ge=1, le=15)],
    product_image: Annotated[UploadFile | None, File(alias="productImage")] = None,
) -> TestResponse:
    test = await get_owned_test(db, test_id, current.id, for_update=True)
    prepared_image = await prepare_product_image(product_image)
    try:
        await persist_configuration(
            db=db,
            storage=storage,
            test=test,
            product_description=product_description,
            total_questions=total_questions,
            product_image=prepared_image,
            require_image=False,
        )
    finally:
        if prepared_image is not None:
            await asyncio.to_thread(prepared_image.path.unlink, missing_ok=True)
    await publish_change(request.app.state.notifications, test.id)
    await db.refresh(test)
    return await to_test_response(db, test)
