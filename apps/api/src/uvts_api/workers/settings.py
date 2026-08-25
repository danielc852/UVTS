from collections.abc import Mapping
from typing import Literal

from uvts_api.core.config import Settings

type AgentSettingsName = Literal["questionAgent", "evaluator"]


def settings_for_agent(
    defaults: Settings,
    recorded_settings: Mapping[str, object] | None,
    *,
    agent: AgentSettingsName,
) -> Settings:
    """Restore the model and timeout recorded when an agent operation started."""
    if recorded_settings is None:
        return defaults

    agent_settings = recorded_settings.get(agent)
    if not isinstance(agent_settings, dict):
        return defaults

    model = agent_settings.get("model")
    timeout = agent_settings.get("requestTimeoutSeconds")
    updates: dict[str, object] = {}
    if isinstance(model, str) and model.strip():
        updates["openrouter_model"] = model
    if isinstance(timeout, int) and not isinstance(timeout, bool) and timeout > 0:
        updates["openrouter_request_timeout_seconds"] = timeout
    return defaults.model_copy(update=updates)
