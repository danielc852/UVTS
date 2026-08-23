from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False
    field_errors: dict[str, list[str]] | None = None
    details: dict[str, Any] | list[Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str = Field(description="ID used to correlate the response with server logs")
