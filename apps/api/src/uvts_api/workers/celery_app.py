from typing import Any

from celery import Celery, signals

from uvts_api.core.config import get_settings
from uvts_api.core.logging import configure_logging, reset_log_context, set_log_context

settings = get_settings()
configure_logging(
    service="uvts-worker",
    environment=settings.environment,
    level=settings.log_level,
)
celery_app = Celery(
    "uvts",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "uvts_api.workers.documents",
        "uvts_api.workers.evaluation",
        "uvts_api.workers.questions",
    ],
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_hijack_root_logger=False,
)


@signals.setup_logging.connect  # type: ignore[untyped-decorator]
def configure_worker_logging(**_: Any) -> None:
    """Keep Celery from replacing the application's safe JSON logging."""

    configure_logging(
        service="uvts-worker",
        environment=settings.environment,
        level=settings.log_level,
    )


@signals.task_prerun.connect  # type: ignore[untyped-decorator]
def bind_task_logging_context(
    *, task_id: str | None = None, task: Any = None, **_: Any
) -> None:
    if task is None:
        return
    token = set_log_context(task_id=task_id or "unknown", task_name=task.name)
    task.request._uvts_logging_context_token = token


@signals.task_postrun.connect  # type: ignore[untyped-decorator]
def clear_task_logging_context(*, task: Any = None, **_: Any) -> None:
    token = getattr(getattr(task, "request", None), "_uvts_logging_context_token", None)
    if token is not None:
        reset_log_context(token)


@celery_app.task(name="uvts.worker.ping")  # type: ignore[untyped-decorator]
def ping() -> str:
    return "pong"
