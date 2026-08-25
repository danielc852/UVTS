import pytest
from pydantic import SecretStr, ValidationError

from uvts_api.adapters.ai import openrouter
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


@pytest.mark.parametrize("value", [0, 16])
def test_evaluation_concurrency_must_match_question_limits(value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(EVALUATION_MAX_CONCURRENCY=value)


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


def test_openrouter_timeout_is_converted_from_seconds_to_milliseconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_options: dict[str, object] = {}

    def capture_model_options(**options: object) -> object:
        captured_options.update(options)
        return object()

    monkeypatch.setattr(openrouter, "ChatOpenRouter", capture_model_options)
    settings = Settings().model_copy(
        update={
            "openrouter_api_key": SecretStr("test-key"),
            "openrouter_request_timeout_seconds": 60,
        }
    )

    build_openrouter_model(settings)

    assert captured_options["request_timeout"] == 60_000


def test_openrouter_api_key_is_trimmed_before_sdk_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_options: dict[str, object] = {}

    def capture_model_options(**options: object) -> object:
        captured_options.update(options)
        return object()

    monkeypatch.setattr(openrouter, "ChatOpenRouter", capture_model_options)
    settings = Settings().model_copy(
        update={"openrouter_api_key": SecretStr("  test-key\n")}
    )

    build_openrouter_model(settings)

    api_key = captured_options["openrouter_api_key"]
    assert isinstance(api_key, SecretStr)
    assert api_key.get_secret_value() == "test-key"
