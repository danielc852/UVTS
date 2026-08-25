import asyncio

from uvts_api.services.documents import process_pending_document
from uvts_api.workers.celery_app import celery_app
from uvts_api.workers.runtime import open_worker_runtime


@celery_app.task(name="uvts.documents.process")  # type: ignore[untyped-decorator]
def process_document(document_id: str) -> None:
    asyncio.run(_process_document(document_id))


async def _process_document(document_id: str) -> None:
    async with open_worker_runtime() as runtime:
        await process_pending_document(
            db=runtime.db,
            storage=runtime.storage,
            notifications=runtime.notifications,
            document_id=document_id,
        )


def enqueue_document_processing(document_id: str) -> None:
    celery_app.send_task("uvts.documents.process", args=[document_id])
