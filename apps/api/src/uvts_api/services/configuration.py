from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from uvts_api.adapters.db.models import Document, TestRun
from uvts_api.core.errors import AppError
from uvts_api.domain.enums import TestStatus
from uvts_api.ports.storage import DocumentStorage
from uvts_api.schemas.workspace import (
    ProductImageSummary,
    QuestionSetStatus,
    TestConfiguration,
    WorkflowStage,
)
from uvts_api.services.documents import delete_storage_after_commit
from uvts_api.services.workspace import load_workspace_state, update_state


@dataclass(frozen=True)
class ProductImageUpload:
    path: Path
    filename: str
    content_type: str
    size_bytes: int


def validated_description(value: str) -> str:
    description = value.strip()
    if not description:
        raise AppError(
            status_code=422,
            code="product_description_required",
            message="Describe the product before saving the question setup.",
            field_errors={
                "productDescription": [
                    "Describe the product before saving the question setup."
                ]
            },
        )
    return description


async def persist_configuration(
    *,
    db: AsyncSession,
    storage: DocumentStorage,
    test: TestRun,
    product_description: str,
    total_questions: int,
    product_image: ProductImageUpload | None,
    require_image: bool,
) -> None:
    """Persist product setup as one database and storage transition."""

    state = await load_workspace_state(db, test)
    if test.active_operation_id is not None:
        raise AppError(
            status_code=409,
            code="operation_in_progress",
            message="Wait for the current operation to finish before changing Product setup.",
            retryable=True,
        )
    if (
        state.question_set is not None
        and state.question_set.status == QuestionSetStatus.CONFIRMED
    ):
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
                "productImage": [
                    "Add a product image before saving the question setup."
                ]
            },
        )

    new_storage_key: str | None = None
    old_storage_key: str | None = None
    image_summary = state.configuration.product_image
    try:
        if product_image is not None:
            new_storage_key = f"{uuid4()}.image"
            await storage.put(new_storage_key, product_image.path)
            if existing is not None:
                old_storage_key = existing.storage_key
                await db.delete(existing)
                await db.flush()
            replacement = Document(
                test_run_id=test.id,
                role="product_image",
                filename=product_image.filename,
                storage_key=new_storage_key,
                status="ready",
            )
            db.add(replacement)
            await db.flush()
            image_summary = ProductImageSummary(
                id=replacement.id,
                filename=product_image.filename,
                content_type=product_image.content_type,
                size_bytes=product_image.size_bytes,
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

    if old_storage_key is not None:
        await delete_storage_after_commit(storage, old_storage_key)
