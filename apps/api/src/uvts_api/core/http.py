import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from uvts_api.core.errors import AppError
from uvts_api.core.logging import reset_log_context, set_log_context
from uvts_api.schemas.errors import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = request.headers.get("X-Request-ID") or str(uuid4())
        token = set_log_context(request_id=request_id(request))
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id(request)
            return response
        finally:
            reset_log_context(token)


def error_response(request: Request, error: ErrorDetail, status_code: int) -> JSONResponse:
    body = ErrorResponse(error=error, request_id=request_id(request))
    return JSONResponse(status_code=status_code, content=jsonable_encoder(body))


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return error_response(
            request,
            ErrorDetail(
                code=exc.code,
                message=exc.message,
                retryable=exc.retryable,
                field_errors=exc.field_errors,
                details=exc.details,
            ),
            exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        field_errors: dict[str, list[str]] = {}
        for item in exc.errors():
            location = ".".join(str(part) for part in item["loc"] if part not in {"body", "query"})
            field_errors.setdefault(location or "request", []).append(str(item["msg"]))
        return error_response(
            request,
            ErrorDetail(
                code="validation_error",
                message="Some request values are invalid.",
                field_errors=field_errors,
                details=exc.errors(),
            ),
            422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return error_response(
            request,
            ErrorDetail(code="http_error", message=str(exc.detail)),
            exc.status_code,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unexpected API request failure",
            extra={
                "request_id": request_id(request),
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "error_type": type(exc).__name__,
            },
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return error_response(
            request,
            ErrorDetail(
                code="internal_error",
                message="UVTS could not complete the request.",
                retryable=True,
            ),
            500,
        )
