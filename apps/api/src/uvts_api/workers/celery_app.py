from celery import Celery

from uvts_api.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "uvts",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["uvts_api.workers.documents"],
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="uvts.worker.ping")  # type: ignore[untyped-decorator]
def ping() -> str:
    return "pong"
