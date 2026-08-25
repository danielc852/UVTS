import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from uvts_api.adapters.db.models import Document, TestRun
from uvts_api.core.errors import AppError
from uvts_api.ports.question_generator import (
    AgentProductImage,
    QuestionDesign,
    QuestionGenerationInput,
)
from uvts_api.ports.storage import DocumentStorage
from uvts_api.services.workspace import load_workspace_state


async def build_question_generation_input(
    *,
    db: AsyncSession,
    storage: DocumentStorage,
    test: TestRun,
) -> QuestionGenerationInput:
    state = await load_workspace_state(db, test)
    configuration = state.configuration
    image = configuration.product_image
    description = configuration.product_description.strip()
    if image is None or not description:
        raise AppError(
            status_code=409,
            code="question_configuration_incomplete",
            message="Save a product image and description before creating questions.",
        )

    document = await db.scalar(
        select(Document).where(
            Document.id == image.id,
            Document.test_run_id == test.id,
            Document.role == "product_image",
        )
    )
    if document is None:
        raise AppError(
            status_code=409,
            code="product_image_missing",
            message="The saved product image is unavailable. Upload it again.",
            retryable=True,
        )
    try:
        path = await storage.local_path(document.storage_key)
        content = await asyncio.to_thread(path.read_bytes)
    except FileNotFoundError as exc:
        raise AppError(
            status_code=409,
            code="product_image_missing",
            message="The saved product image is unavailable. Upload it again.",
            retryable=True,
        ) from exc

    return QuestionGenerationInput(
        product_image=AgentProductImage(
            content=content,
            content_type=image.content_type,
            filename=image.filename,
        ),
        product_description=description,
        question_design=QuestionDesign(total_questions=configuration.total_questions),
    )
