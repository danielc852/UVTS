from collections.abc import Mapping
from typing import Literal

from uvts_api.core.config import OPENROUTER_REASONING_EFFORTS, Settings

type AgentSettingsName = Literal["questionAgent", "evaluator"]


def settings_for_agent(
    defaults: Settings,
    recorded_settings: Mapping[str, object] | None,
    *,
    agent: AgentSettingsName,
) -> Settings:
    """Restore the model routing, reasoning effort, and timeout recorded at startup."""
    if recorded_settings is None:
        return defaults

    agent_settings = recorded_settings.get(agent)
    if not isinstance(agent_settings, dict):
        return defaults

    model = agent_settings.get("model")
    fallback_model = agent_settings.get("fallbackModel")
    reasoning_effort = agent_settings.get("reasoningEffort")
    timeout = agent_settings.get("requestTimeoutSeconds")
    updates: dict[str, object] = {}
    if isinstance(model, str) and model.strip():
        updates["openrouter_model"] = model
    if isinstance(fallback_model, str):
        updates["openrouter_fallback_model"] = fallback_model.strip()
    if isinstance(reasoning_effort, str) and reasoning_effort in OPENROUTER_REASONING_EFFORTS:
        updates["openrouter_reasoning_effort"] = reasoning_effort
    if isinstance(timeout, int) and not isinstance(timeout, bool) and timeout > 0:
        updates["openrouter_request_timeout_seconds"] = timeout
    return defaults.model_copy(update=updates)
