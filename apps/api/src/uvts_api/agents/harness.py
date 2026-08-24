import asyncio
import logging
from collections.abc import Mapping
from time import monotonic
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain_core.language_models.chat_models import BaseChatModel

from uvts_api.ports.model_gateway import ModelOutput

logger = logging.getLogger(__name__)

_SAFE_METADATA_KEYS = frozenset({"operation_id", "question_id", "test_id"})


class AgentExecutionError(RuntimeError):
    """A model request failed after the configured bounded attempts."""


class LangChainAgentHarness:
    def __init__(
        self,
        model: BaseChatModel,
        *,
        timeout_seconds: float = 60.0,
        max_attempts: int = 3,
    ) -> None:
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts

    async def request_structured(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        prompt: str,
        output_type: type[ModelOutput],
        metadata: Mapping[str, Any],
    ) -> ModelOutput:
        safe_metadata = {
            key: str(value) for key, value in metadata.items() if key in _SAFE_METADATA_KEYS
        }
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            started_at = monotonic()
            try:
                agent = create_agent(
                    model=self._model,
                    tools=[],
                    name=agent_name,
                    system_prompt=system_prompt,
                    response_format=ProviderStrategy(output_type, strict=True),
                )
                result = await asyncio.wait_for(
                    agent.ainvoke({"messages": [{"role": "user", "content": prompt}]}),
                    timeout=self._timeout_seconds,
                )
                structured = result.get("structured_response")
                if not isinstance(structured, output_type):
                    structured = output_type.model_validate(structured)
                logger.info(
                    "Agent run succeeded",
                    extra={
                        "agent_name": agent_name,
                        "agent_attempt": attempt,
                        "agent_duration_seconds": monotonic() - started_at,
                        "agent_metadata": safe_metadata,
                        "agent_usage": _usage_metadata(result),
                    },
                )
                return structured
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Agent run failed",
                    extra={
                        "agent_name": agent_name,
                        "agent_attempt": attempt,
                        "agent_duration_seconds": monotonic() - started_at,
                        "agent_metadata": safe_metadata,
                        "agent_error_type": type(exc).__name__,
                    },
                )
                if attempt < self._max_attempts:
                    await asyncio.sleep(min(0.25 * (2 ** (attempt - 1)), 1.0))
        raise AgentExecutionError(
            f"{agent_name} failed after {self._max_attempts} attempts"
        ) from last_error


def _usage_metadata(result: Mapping[str, Any]) -> Mapping[str, Any]:
    messages = result.get("messages")
    if not isinstance(messages, list) or not messages:
        return {}
    usage = getattr(messages[-1], "usage_metadata", None)
    return usage if isinstance(usage, Mapping) else {}
