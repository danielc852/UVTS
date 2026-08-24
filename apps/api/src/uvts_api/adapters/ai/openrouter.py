from langchain_openrouter import ChatOpenRouter

from uvts_api.core.config import Settings


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
