"""Central, payload-safe logging configuration for API and worker processes."""

from __future__ import annotations

import json
import logging
import re
import traceback
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

_LOG_CONTEXT: ContextVar[dict[str, object] | None] = ContextVar(
    "uvts_log_context", default=None
)

_STANDARD_RECORD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__) | {
    "asctime",
    "message",
}

# Log records may carry only operational metadata. Request bodies, prompts, manual
# text, model messages, and image data are deliberately absent from this list.
_SAFE_EXTRA_FIELDS = frozenset(
    {
        "attempt",
        "document_id",
        "duration_ms",
        "error_message",
        "error_stage",
        "error_type",
        "event",
        "method",
        "model",
        "operation_id",
        "path",
        "provider",
        "question_id",
        "request_id",
        "stage",
        "status",
        "status_code",
        "storage_key",
        "task_id",
        "task_name",
        "test_id",
    }
)

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(['\"]?(?:authorization|api[-_]?key|password|secret|session[-_]?token|token)['\"]?)"
    r"(\s*[:=]\s*)(['\"][^'\"]*['\"]|[^\s,;]+)",
)
_BEARER_TOKEN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+\-/]+=*")
_URL_CREDENTIALS = re.compile(r"(?P<scheme>\b[a-z][a-z0-9+.-]*://)[^/@\s]+@", re.IGNORECASE)
_PYDANTIC_INPUT = re.compile(
    r"(?s)input_(?:value|value_repr)\s*=\s*.*?(?=,?\s*input_type\s*=|\]|$)"
)
_DATA_URL = re.compile(r"data:(?:image|application)/[^;,\s]+;base64,[A-Za-z0-9+/=]+")
_LONG_BASE64 = re.compile(r"\b[A-Za-z0-9+/]{256,}={0,2}\b")


def set_log_context(**values: object) -> Token[dict[str, object] | None]:
    """Add safe correlation values to every log emitted in the current context."""

    safe_values = {key: value for key, value in values.items() if key in _SAFE_EXTRA_FIELDS}
    return _LOG_CONTEXT.set({**(_LOG_CONTEXT.get() or {}), **safe_values})


def reset_log_context(token: Token[dict[str, object] | None]) -> None:
    """Restore the logging context that existed before ``set_log_context``."""

    _LOG_CONTEXT.reset(token)


def _sanitize_text(value: str, *, limit: int = 2_048) -> str:
    sanitized = _SECRET_ASSIGNMENT.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[redacted]", value
    )
    sanitized = _BEARER_TOKEN.sub("Bearer [redacted]", sanitized)
    sanitized = _URL_CREDENTIALS.sub(r"\g<scheme>[redacted]@", sanitized)
    sanitized = _PYDANTIC_INPUT.sub("input_value=[redacted]", sanitized)
    sanitized = _DATA_URL.sub("[redacted image data]", sanitized)
    sanitized = _LONG_BASE64.sub("[redacted binary data]", sanitized)
    if len(sanitized) <= limit:
        return sanitized
    return f"{sanitized[:limit]}…[truncated]"


def _safe_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value[:20]]
    if isinstance(value, dict):
        return {
            str(key): _safe_value(item)
            for key, item in list(value.items())[:20]
            if str(key) in _SAFE_EXTRA_FIELDS
        }
    return _sanitize_text(str(value))


def _exception_details(exc_info: Any) -> dict[str, object] | None:
    if not exc_info or not isinstance(exc_info, tuple) or exc_info[1] is None:
        return None
    error = cast(BaseException, exc_info[1])
    frames = traceback.extract_tb(exc_info[2]) if exc_info[2] is not None else []
    details: dict[str, object] = {
        "type": type(error).__name__,
        "traceback": [
            {
                "file": frame.filename,
                "line": frame.lineno,
                "function": frame.name,
            }
            for frame in frames
        ],
    }
    if getattr(error, "safe_for_logging", False) is True:
        details["message"] = _sanitize_text(str(error), limit=1_024)
    return details


class SafeJsonFormatter(logging.Formatter):
    """Render logs as JSON while excluding application and model payloads."""

    def __init__(self, *, service: str, environment: str) -> None:
        super().__init__()
        self._service = service
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "service": self._service,
            "environment": self._environment,
            "logger": record.name,
            "message": _sanitize_text(record.getMessage()),
        }
        for key, value in (_LOG_CONTEXT.get() or {}).items():
            if key in _SAFE_EXTRA_FIELDS:
                payload[key] = _safe_value(value)
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_FIELDS and key in _SAFE_EXTRA_FIELDS:
                payload[key] = _safe_value(value)
        exception = _exception_details(record.exc_info)
        if exception is not None:
            payload["exception"] = exception
        if record.stack_info:
            payload["stack"] = _sanitize_text(record.stack_info)
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def configure_logging(*, service: str, environment: str, level: str = "INFO") -> None:
    """Install one consistent logging configuration for a UVTS process."""

    normalized_level = level.upper()
    if normalized_level not in logging.getLevelNamesMapping():
        normalized_level = "INFO"
    formatter = SafeJsonFormatter(service=service, environment=environment)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(normalized_level)

    # Uvicorn and Celery normally install private handlers that bypass the root
    # formatter. Propagation makes their records use the same safe JSON output.
    for logger_name in (
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "celery",
        "celery.app.trace",
        "celery.task",
    ):
        named_logger = logging.getLogger(logger_name)
        named_logger.handlers.clear()
        named_logger.setLevel(logging.NOTSET)
        named_logger.propagate = True
