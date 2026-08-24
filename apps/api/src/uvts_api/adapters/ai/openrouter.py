from langchain_openrouter import ChatOpenRouter

from uvts_api.core.config import Settings


def is_openrouter_configured(settings: Settings) -> bool:
    api_key = settings.openrouter_api_key
    return bool(api_key and api_key.get_secret_value().strip())


def build_openrouter_model(settings: Settings, *, temperature: float = 0.0) -> ChatOpenRouter:
    if not is_openrouter_configured(settings):
        raise RuntimeError("OpenRouter integration is not configured")
    return ChatOpenRouter(
        model_name=settings.openrouter_model,
        openrouter_api_key=settings.openrouter_api_key,
        temperature=temperature,
        request_timeout=settings.openrouter_request_timeout_seconds,
        max_retries=2,
        openrouter_provider={"require_parameters": True},
    )
