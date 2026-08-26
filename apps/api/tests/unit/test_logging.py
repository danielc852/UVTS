import inspect
import json
import logging
import sys
from io import StringIO
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from starlette.requests import Request

from uvts_api import main
from uvts_api.core import http
from uvts_api.core.config import Settings
from uvts_api.core.logging import (
    SafeJsonFormatter,
    configure_logging,
    reset_log_context,
    set_log_context,
)
from uvts_api.workers import celery_app as worker_logging
from uvts_api.workers.celery_app import bind_task_logging_context, clear_task_logging_context


def _render_record(record: logging.LogRecord) -> dict[str, object]:
    formatter = SafeJsonFormatter(service="test-service", environment="test")
    return cast(dict[str, object], json.loads(formatter.format(record)))


def test_formatter_renders_safe_extra_fields_and_context() -> None:
    token = set_log_context(request_id="request-1")
    try:
        record = logging.LogRecord(
            name="uvts_api.test",
            level=logging.WARNING,
            pathname=__file__,
            lineno=1,
            msg="Evaluation failed",
            args=(),
            exc_info=None,
        )
        record.test_id = "test-1"
        record.question_id = "question-1"
        record.error_stage = "response_validation"

        rendered = _render_record(record)
    finally:
        reset_log_context(token)

    assert rendered["service"] == "test-service"
    assert rendered["environment"] == "test"
    assert rendered["request_id"] == "request-1"
    assert rendered["test_id"] == "test-1"
    assert rendered["question_id"] == "question-1"
    assert rendered["error_stage"] == "response_validation"


def test_formatter_omits_payload_fields_and_redacts_sensitive_text() -> None:
    record = logging.LogRecord(
        name="uvts_api.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Call failed with api_key=%s",
        args=("top-secret",),
        exc_info=None,
    )
    record.prompt = "private prompt"
    record.manual_pages = "private manual text"
    record.product_image = "data:image/png;base64,AAAA"

    rendered = _render_record(record)
    encoded = json.dumps(rendered)

    assert "top-secret" not in encoded
    assert "private prompt" not in encoded
    assert "private manual text" not in encoded
    assert "data:image" not in encoded
    assert "[redacted]" in encoded


def test_formatter_redacts_quoted_secrets_and_url_credentials() -> None:
    record = logging.LogRecord(
        name="uvts_api.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg='Request failed: {"api_key": "private key"} at redis://user:pass@cache/0',
        args=(),
        exc_info=None,
    )

    encoded = json.dumps(_render_record(record))

    assert "private key" not in encoded
    assert "user:pass" not in encoded
    assert encoded.count("[redacted]") >= 2


def test_formatter_omits_untrusted_exception_message_but_keeps_traceback() -> None:
    try:
        raise ValueError("input_value='private manual text', input_type=str token=secret")
    except ValueError:
        record = logging.getLogger("uvts_api.test").makeRecord(
            "uvts_api.test",
            logging.ERROR,
            __file__,
            1,
            "Evaluation response was rejected",
            (),
            exc_info=__import__("sys").exc_info(),
        )

    rendered = _render_record(record)
    exception = rendered["exception"]

    assert isinstance(exception, dict)
    assert exception["type"] == "ValueError"
    assert "message" not in exception
    assert "private manual text" not in str(exception)
    assert "secret" not in str(exception)
    assert exception["traceback"]


def test_formatter_includes_message_for_explicitly_safe_exception() -> None:
    class SafeDiagnosticError(RuntimeError):
        safe_for_logging = True

    try:
        raise SafeDiagnosticError("Evidence is not an exact extract from its page.")
    except SafeDiagnosticError:
        record = logging.getLogger("uvts_api.test").makeRecord(
            "uvts_api.test",
            logging.ERROR,
            __file__,
            1,
            "Evaluation response was rejected",
            (),
            exc_info=sys.exc_info(),
        )

    exception = _render_record(record)["exception"]

    assert isinstance(exception, dict)
    assert exception["message"] == "Evidence is not an exact extract from its page."


def test_configure_logging_outputs_json_with_extra_fields() -> None:
    configure_logging(service="uvts-api", environment="test", level="WARNING")
    stream = StringIO()
    root_handler = logging.getLogger().handlers[0]
    assert isinstance(root_handler, logging.StreamHandler)
    try:
        root_handler.setStream(stream)
        logging.getLogger("uvts_api.test").warning(
            "Question evaluation failed",
            extra={"question_id": "question-1", "error_type": "ValueError"},
        )
    finally:
        root_handler.setStream(sys.stderr)

    rendered = json.loads(stream.getvalue())
    assert rendered["service"] == "uvts-api"
    assert rendered["question_id"] == "question-1"
    assert rendered["error_type"] == "ValueError"


def test_worker_task_context_is_bound_and_cleared() -> None:
    task = SimpleNamespace(name="uvts.evaluation.process", request=SimpleNamespace())

    bind_task_logging_context(task_id="task-1", task=task)
    active = _render_record(
        logging.LogRecord("uvts_api.test", logging.INFO, __file__, 1, "active", (), None)
    )
    clear_task_logging_context(task=task)
    cleared = _render_record(
        logging.LogRecord("uvts_api.test", logging.INFO, __file__, 1, "cleared", (), None)
    )

    assert active["task_id"] == "task-1"
    assert active["task_name"] == "uvts.evaluation.process"
    assert "task_id" not in cleared


def test_api_factory_configures_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, str]] = []
    monkeypatch.setattr(main, "configure_logging", lambda **options: calls.append(options))
    settings = Settings(environment="production", log_level="WARNING")

    main.create_app(settings)

    assert calls == [
        {
            "service": "uvts-api",
            "environment": "production",
            "level": "WARNING",
        }
    ]


def test_worker_logging_signal_reapplies_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, str]] = []
    monkeypatch.setattr(
        worker_logging,
        "configure_logging",
        lambda **options: calls.append(options),
    )

    worker_logging.configure_worker_logging()

    assert calls == [
        {
            "service": "uvts-worker",
            "environment": worker_logging.settings.environment,
            "level": worker_logging.settings.log_level,
        }
    ]


async def test_unexpected_api_error_is_logged_with_request_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    http.install_error_handlers(app)
    error_logger = Mock(spec=logging.Logger)
    monkeypatch.setattr(http, "logger", error_logger)
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/explode",
            "root_path": "",
            "query_string": b"secret=query-is-not-logged",
            "headers": [],
            "client": ("test", 123),
            "server": ("test", 80),
        }
    )
    request.state.request_id = "request-1"
    error = RuntimeError("task failed")

    response_or_awaitable = app.exception_handlers[Exception](request, error)
    response = (
        await response_or_awaitable
        if inspect.isawaitable(response_or_awaitable)
        else response_or_awaitable
    )

    assert response.status_code == 500
    error_logger.error.assert_called_once_with(
        "Unexpected API request failure",
        extra={
            "request_id": "request-1",
            "method": "GET",
            "path": "/explode",
            "status_code": 500,
            "error_type": "RuntimeError",
        },
        exc_info=(RuntimeError, error, error.__traceback__),
    )
