import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, File, Form, Request, UploadFile
from sqlalchemy import select

from uvts_api.adapters.db.models import Document, TestRun
from uvts_api.api.dependencies import CurrentSession, DatabaseSession, DocumentStorageDependency
from uvts_api.core.errors import AppError
from uvts_api.domain.enums import TestStatus
from uvts_api.schemas.errors import ErrorResponse
from uvts_api.schemas.tests import TestResponse
from uvts_api.schemas.workspace import (
    ProductImageSummary,
    QuestionSetStatus,
    TestConfiguration,
    WorkflowStage,
    WorkspaceState,
)
from uvts_api.services.documents import (
    delete_storage_after_commit,
    publish_change,
    update_state,
)
from uvts_api.services.tests import get_owned_test, to_test_response

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


def validated_description(value: str) -> str:
    description = value.strip()
    if not description:
        raise AppError(
            status_code=422,
            code="product_description_required",
            message="Describe the product before saving the question setup.",
            field_errors={
                "productDescription": ["Describe the product before saving the question setup."]
            },
        )
    return description


async def persist_configuration(
    *,
    db: DatabaseSession,
    storage: DocumentStorageDependency,
    test: TestRun,
    product_description: str,
    total_questions: int,
    product_image: UploadFile | None,
    require_image: bool,
) -> None:
    state = WorkspaceState.model_validate(test.state)
    if test.active_operation_id is not None:
        raise AppError(
            status_code=409,
            code="operation_in_progress",
            message="Wait for the current operation to finish before changing Product setup.",
            retryable=True,
        )
    if state.question_set is not None and state.question_set.status == QuestionSetStatus.CONFIRMED:
        raise AppError(
            status_code=409,
            code="configuration_locked",
            message="Start over before changing Product setup for confirmed questions.",
        )

    description = validated_description(product_description)
    existing = await db.scalar(
        select(Document).where(
            Document.test_run_id == test.id,
            Document.role == "product_image",
        )
    )
    if product_image is None and (require_image or existing is None):
        raise AppError(
            status_code=422,
            code="product_image_required",
            message="Add a product image before saving the question setup.",
            field_errors={
                "productImage": ["Add a product image before saving the question setup."]
            },
        )

    temporary: Path | None = None
    new_storage_key: str | None = None
    old_storage_key: str | None = None
    image_summary = state.configuration.product_image
    try:
        if product_image is not None:
            filename = safe_image_filename(product_image)
            content_type = product_image.content_type or ""
            temporary, size_bytes = await save_temporary_image(product_image)
            new_storage_key = f"{uuid4()}.image"
            await storage.put(new_storage_key, temporary)
            if existing is not None:
                old_storage_key = existing.storage_key
                await db.delete(existing)
                await db.flush()
            replacement = Document(
                test_run_id=test.id,
                role="product_image",
                filename=filename,
                storage_key=new_storage_key,
                status="ready",
            )
            db.add(replacement)
            await db.flush()
            image_summary = ProductImageSummary(
                id=replacement.id,
                filename=filename,
                content_type=content_type,
                size_bytes=size_bytes,
            )

        assert image_summary is not None
        configuration = TestConfiguration(
            version=state.configuration.version + 1,
            product_image=image_summary,
            product_description=description,
            total_questions=total_questions,
        )
        next_stage = (
            WorkflowStage.QUESTIONS
            if state.question_set is not None
            else WorkflowStage.CONFIGURATION
        )
        update_state(
            test,
            state.model_copy(
                update={
                    "current_stage": next_stage,
                    "configuration": configuration,
                    "error": None,
                }
            ),
        )
        test.status = (
            TestStatus.QUESTIONS_READY.value
            if state.question_set is not None
            else TestStatus.DRAFT.value
        )
        await db.commit()
    except Exception:
        await db.rollback()
        if new_storage_key is not None:
            await delete_storage_after_commit(storage, new_storage_key)
        raise
    finally:
        if temporary is not None:
            await asyncio.to_thread(temporary.unlink, missing_ok=True)

    if old_storage_key is not None:
        await delete_storage_after_commit(storage, old_storage_key)


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
    test = TestRun(
        owner_session_id=current.id,
        state=WorkspaceState().model_dump(mode="json", by_alias=True),
    )
    db.add(test)
    await db.flush()
    await persist_configuration(
        db=db,
        storage=storage,
        test=test,
        product_description=product_description,
        total_questions=total_questions,
        product_image=product_image,
        require_image=True,
    )
    await publish_change(request.app.state.notifications, test.id)
    await db.refresh(test)
    return to_test_response(test)


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
    await persist_configuration(
        db=db,
        storage=storage,
        test=test,
        product_description=product_description,
        total_questions=total_questions,
        product_image=product_image,
        require_image=False,
    )
    await publish_change(request.app.state.notifications, test.id)
    await db.refresh(test)
    return to_test_response(test)
