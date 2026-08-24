from langchain_openrouter import ChatOpenRouter

from uvts_api.adapters.ai.not_configured import NotConfiguredModelGateway
from uvts_api.agents.harness import LangChainAgentHarness
from uvts_api.core.config import Settings
from uvts_api.ports.model_gateway import ModelGateway


def build_openrouter_model(settings: Settings, *, temperature: float = 0.0) -> ChatOpenRouter:
    if settings.openrouter_api_key is None:
        raise RuntimeError("OpenRouter integration is not configured")
    return ChatOpenRouter(
        model_name=settings.openrouter_model,
        openrouter_api_key=settings.openrouter_api_key,
        temperature=temperature,
        request_timeout=settings.openrouter_request_timeout_seconds,
        max_retries=0,
        openrouter_provider={"require_parameters": True},
    )


def build_model_gateway(settings: Settings) -> ModelGateway:
    if settings.openrouter_api_key is None:
        return NotConfiguredModelGateway()
    return LangChainAgentHarness(
        build_openrouter_model(settings),
        timeout_seconds=settings.openrouter_request_timeout_seconds,
        max_attempts=settings.agent_max_attempts,
    )
