from collections.abc import Awaitable, Callable, Sequence
from typing import cast

from fastapi import Request
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from uvts_api.adapters.ai.openrouter import build_openrouter_model
from uvts_api.agents.evaluator import EvaluatorAgent
from uvts_api.core.config import Settings
from uvts_api.ports.notifications import StateNotifications
from uvts_api.ports.storage import DocumentStorage
from uvts_api.services.documents import process_pending_document
from uvts_api.services.evaluation import (
    fail_evaluation_dispatch,
    process_evaluation_operation,
)
from uvts_api.services.questions import (
    build_question_agent,
    fail_question_generation,
    process_question_generation,
)
from uvts_api.workers.documents import enqueue_document_processing
from uvts_api.workers.evaluation import enqueue_evaluation_processing
from uvts_api.workers.questions import enqueue_question_generation

EagerOperation = Callable[[], Awaitable[None]]
QueuedOperation = Callable[[], None]
DispatchFailureHandler = Callable[[Exception], Awaitable[None]]


class OperationDispatcher:
    """Dispatch API-started background work in-process or through the queue."""

    def __init__(
        self,
        *,
        request: Request,
        db: AsyncSession,
        storage: DocumentStorage,
        settings: Settings,
    ) -> None:
        self._request = request
        self._db = db
        self._storage = storage
        self._settings = settings
        self._notifications = cast(StateNotifications, request.app.state.notifications)

    async def process_document(self, document_id: str) -> None:
        def process_eagerly() -> Awaitable[None]:
            return process_pending_document(
                db=self._db,
                storage=self._storage,
                notifications=self._notifications,
                document_id=document_id,
            )

        await self._dispatch(
            eager=self._settings.document_processing_eager,
            process_eagerly=process_eagerly,
            enqueue=lambda: enqueue_document_processing(document_id),
        )

    async def generate_questions(self, *, test_id: str, operation_id: str) -> None:
        def process_eagerly() -> Awaitable[None]:
            agent = build_question_agent(self._settings)
            return process_question_generation(
                db=self._db,
                storage=self._storage,
                notifications=self._notifications,
                agent=agent,
                test_id=test_id,
                operation_id=operation_id,
            )

        async def dispatch_failed(error: Exception) -> None:
            await fail_question_generation(
                db=self._db,
                notifications=self._notifications,
                test_id=test_id,
                operation_id=operation_id,
                error=error,
            )

        await self._dispatch(
            eager=self._settings.agent_processing_eager,
            process_eagerly=process_eagerly,
            enqueue=lambda: enqueue_question_generation(test_id, operation_id),
            dispatch_failed=dispatch_failed,
        )

    async def evaluate(
        self,
        *,
        test_id: str,
        operation_id: str,
        question_ids: Sequence[str],
    ) -> None:
        def process_eagerly() -> Awaitable[None]:
            agent = self._request_evaluator()
            return process_evaluation_operation(
                db=self._db,
                storage=self._storage,
                agent=agent,
                notifications=self._notifications,
                test_id=test_id,
                operation_id=operation_id,
                question_ids=question_ids,
            )

        async def dispatch_failed(error: Exception) -> None:
            await fail_evaluation_dispatch(
                db=self._db,
                notifications=self._notifications,
                test_id=test_id,
                operation_id=operation_id,
                question_ids=question_ids,
                error=error,
            )

        await self._dispatch(
            eager=self._settings.agent_processing_eager,
            process_eagerly=process_eagerly,
            enqueue=lambda: enqueue_evaluation_processing(
                test_id, operation_id, question_ids
            ),
            dispatch_failed=dispatch_failed,
        )

    async def _dispatch(
        self,
        *,
        eager: bool,
        process_eagerly: EagerOperation,
        enqueue: QueuedOperation,
        dispatch_failed: DispatchFailureHandler | None = None,
    ) -> None:
        if not eager:
            try:
                enqueue()
            except Exception as error:
                if dispatch_failed is None:
                    raise
                await dispatch_failed(error)
            return

        try:
            operation = process_eagerly()
        except Exception as error:
            if dispatch_failed is None:
                raise
            await dispatch_failed(error)
            return
        await operation

    def _request_evaluator(self) -> EvaluatorAgent:
        configured = getattr(self._request.app.state, "chat_model", None)
        if configured is not None:
            return EvaluatorAgent(cast(BaseChatModel, configured))
        return EvaluatorAgent(build_openrouter_model(self._settings, temperature=0.0))
