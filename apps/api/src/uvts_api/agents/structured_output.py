from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ValidationError

from uvts_api.agents.errors import (
    EvaluatorModelInvocationError,
    EvaluatorRateLimitError,
    EvaluatorStructuredOutputError,
)


async def invoke_structured_output[StructuredModel: BaseModel](
    model: BaseChatModel,
    schema: type[StructuredModel],
    messages: Sequence[BaseMessage],
) -> StructuredModel:
    """Invoke one strict structured model call with safe, shared error handling."""

    try:
        structured_model = model.with_structured_output(
            schema,
            method="json_schema",
            strict=True,
        )
        raw_output = await structured_model.ainvoke(list(messages))
    except (OutputParserException, ValidationError) as error:
        raise EvaluatorStructuredOutputError(type(error).__name__) from None
    except Exception as error:
        is_rate_limit, retry_after_seconds = rate_limit_retry_after_seconds(error)
        if is_rate_limit:
            raise EvaluatorRateLimitError(
                type(error).__name__,
                retry_after_seconds=retry_after_seconds,
            ) from None
        raise EvaluatorModelInvocationError(type(error).__name__) from None

    try:
        return schema.model_validate(raw_output)
    except ValidationError as error:
        raise EvaluatorStructuredOutputError(type(error).__name__) from None


def rate_limit_retry_after_seconds(error: Exception) -> tuple[bool, float | None]:
    """Identify a provider 429 and retain only its safe retry delay."""

    if getattr(error, "status_code", None) != 429:
        return False, None
    headers = getattr(error, "headers", None)
    if not isinstance(headers, Mapping):
        return True, None
    raw_value = headers.get("Retry-After") or headers.get("retry-after")
    if not isinstance(raw_value, str):
        return True, None
    try:
        return True, max(0.0, float(raw_value))
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(raw_value)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        return True, max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
    except (TypeError, ValueError, OverflowError):
        return True, None
