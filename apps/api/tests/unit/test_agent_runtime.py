from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

from uvts_api.agents.errors import (
    EvaluatorFailureStage,
    EvaluatorModelInvocationError,
    EvaluatorOutputError,
    EvaluatorRateLimitError,
    EvaluatorStructuredOutputError,
    describe_evaluator_failure,
)
from uvts_api.agents.structured_output import rate_limit_retry_after_seconds


class ProviderError(RuntimeError):
    def __init__(self, *, status_code: int, retry_after: str | None = None) -> None:
        super().__init__("private provider detail")
        self.status_code = status_code
        self.headers = {"Retry-After": retry_after} if retry_after is not None else {}


def test_rate_limit_parser_accepts_seconds_and_http_dates() -> None:
    is_rate_limit, seconds = rate_limit_retry_after_seconds(
        ProviderError(status_code=429, retry_after="2.5")
    )
    retry_at = datetime.now(UTC) + timedelta(seconds=5)
    is_dated_limit, dated_seconds = rate_limit_retry_after_seconds(
        ProviderError(status_code=429, retry_after=format_datetime(retry_at))
    )

    assert is_rate_limit is True
    assert seconds == 2.5
    assert is_dated_limit is True
    assert dated_seconds is not None
    assert 0 <= dated_seconds <= 5


def test_rate_limit_parser_rejects_non_429_errors() -> None:
    assert rate_limit_retry_after_seconds(ProviderError(status_code=500)) == (False, None)


def test_evaluator_failures_expose_only_safe_diagnostics() -> None:
    cases = [
        (
            EvaluatorModelInvocationError("PrivateProviderError"),
            EvaluatorFailureStage.MODEL_INVOCATION,
        ),
        (
            EvaluatorRateLimitError("PrivateRateError", retry_after_seconds=1),
            EvaluatorFailureStage.MODEL_INVOCATION,
        ),
        (
            EvaluatorStructuredOutputError("ValidationError"),
            EvaluatorFailureStage.STRUCTURED_OUTPUT,
        ),
        (EvaluatorOutputError("private output"), EvaluatorFailureStage.SEMANTIC_VALIDATION),
    ]

    for error, stage in cases:
        details = describe_evaluator_failure(error)
        assert details.stage is stage
        assert "private output" not in details.message.casefold()
