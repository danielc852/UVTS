from langchain_openrouter import ChatOpenRouter
from pydantic import SecretStr

from uvts_api.core.config import Settings


def is_openrouter_configured(settings: Settings) -> bool:
    api_key = settings.openrouter_api_key
    return bool(api_key and api_key.get_secret_value().strip())


def build_openrouter_model(settings: Settings, *, temperature: float = 0.0) -> ChatOpenRouter:
    if not is_openrouter_configured(settings):
        raise RuntimeError("OpenRouter integration is not configured")

    api_key = settings.openrouter_api_key
    assert api_key is not None
    return ChatOpenRouter(
        model_name=settings.openrouter_model,
        openrouter_api_key=SecretStr(api_key.get_secret_value().strip()),
        temperature=temperature,
        request_timeout=settings.openrouter_request_timeout_seconds * 1_000,
        max_retries=2,
        openrouter_provider={"require_parameters": True},
    )
