from typing import Any, cast

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from uvts_api.agents.harness import AgentExecutionError, LangChainAgentHarness


class ExampleOutput(BaseModel):
    value: str


class FakeCompiledAgent:
    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = outcomes

    async def ainvoke(self, payload: object) -> dict[str, Any]:
        del payload
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return {"structured_response": outcome, "messages": []}


@pytest.mark.asyncio
async def test_harness_returns_validated_structured_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compiled = FakeCompiledAgent([{"value": "ready"}])
    monkeypatch.setattr(
        "uvts_api.agents.harness.create_agent", lambda **kwargs: compiled
    )
    harness = LangChainAgentHarness(
        cast(BaseChatModel, object()), timeout_seconds=1, max_attempts=1
    )

    result = await harness.request_structured(
        agent_name="test_agent",
        system_prompt="Return the requested shape.",
        prompt="Private manual contents",
        output_type=ExampleOutput,
        metadata={"test_id": "test-1"},
    )

    assert result == ExampleOutput(value="ready")


@pytest.mark.asyncio
async def test_harness_retries_without_logging_private_metadata(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    compiled = FakeCompiledAgent([TimeoutError(), ExampleOutput(value="recovered")])
    monkeypatch.setattr(
        "uvts_api.agents.harness.create_agent", lambda **kwargs: compiled
    )

    async def skip_sleep(delay: float) -> None:
        del delay

    monkeypatch.setattr("uvts_api.agents.harness.asyncio.sleep", skip_sleep)
    harness = LangChainAgentHarness(
        cast(BaseChatModel, object()), timeout_seconds=1, max_attempts=2
    )

    result = await harness.request_structured(
        agent_name="test_agent",
        system_prompt="Return the requested shape.",
        prompt="Private manual contents",
        output_type=ExampleOutput,
        metadata={"test_id": "test-1", "manual_text": "must-not-be-logged"},
    )

    assert result == ExampleOutput(value="recovered")
    assert all("must-not-be-logged" not in record.getMessage() for record in caplog.records)
    assert all(
        "manual_text" not in getattr(record, "agent_metadata", {}) for record in caplog.records
    )


@pytest.mark.asyncio
async def test_harness_raises_bounded_plain_error(monkeypatch: pytest.MonkeyPatch) -> None:
    compiled = FakeCompiledAgent([RuntimeError("provider secret")])
    monkeypatch.setattr(
        "uvts_api.agents.harness.create_agent", lambda **kwargs: compiled
    )
    harness = LangChainAgentHarness(
        cast(BaseChatModel, object()), timeout_seconds=1, max_attempts=1
    )

    with pytest.raises(AgentExecutionError, match="failed after 1 attempts") as error:
        await harness.request_structured(
            agent_name="test_agent",
            system_prompt="Return the requested shape.",
            prompt="Private manual contents",
            output_type=ExampleOutput,
            metadata={"test_id": "test-1"},
        )

    assert "provider secret" not in str(error.value)
