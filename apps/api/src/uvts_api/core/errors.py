from typing import Any


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        retryable: bool = False,
        field_errors: dict[str, list[str]] | None = None,
        details: dict[str, Any] | list[Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.field_errors = field_errors
        self.details = details


def session_required() -> AppError:
    return AppError(
        status_code=401,
        code="session_required",
        message="Start a private session before continuing.",
    )


def test_not_found() -> AppError:
    # The same response is used for absent and unowned IDs to avoid disclosing private tests.
    return AppError(status_code=404, code="test_not_found", message="This test was not found.")
