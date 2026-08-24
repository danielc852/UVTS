import pytest
from pydantic import SecretStr

from uvts_api.adapters.ai.openrouter import build_openrouter_model, is_openrouter_configured
from uvts_api.core.config import Settings
from uvts_api.core.security import hash_session_token


def test_settings_accept_shared_root_environment_names() -> None:
    # Pydantic constructor aliases are the same names used by the shared root env file.
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///local.db",
        REDIS_URL="redis://cache/4",
        ALLOWED_ORIGINS=["https://app.example"],
        PRIVATE_STORAGE_PATH="/private/documents",
    )

    assert settings.database_url.endswith("local.db")
    assert settings.redis_url == "redis://cache/4"
    assert settings.cors_origins == ["https://app.example"]
    assert str(settings.storage_root) == "/private/documents"


def test_session_hash_is_fixed_length_and_does_not_contain_token() -> None:
    token = "private-cookie-value"
    digest = hash_session_token(token)

    assert len(digest) == 64
    assert token not in digest


def test_blank_openrouter_key_is_not_configured() -> None:
    settings = Settings().model_copy(update={"openrouter_api_key": SecretStr("   ")})

    assert is_openrouter_configured(settings) is False
    with pytest.raises(RuntimeError, match="OpenRouter integration is not configured"):
        build_openrouter_model(settings)
