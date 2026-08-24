from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from uvts_api.core.config import Settings
from uvts_api.main import create_app


class FakeRedis:
    def __init__(self) -> None:
        self.available = True

    async def ping(self) -> bool:
        if not self.available:
            raise ConnectionError("redis unavailable")
        return True

    async def publish(self, channel: str, message: str) -> int:
        del channel, message
        return 0

    async def aclose(self) -> None:
        return None


@pytest.fixture
async def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[FastAPI]:
    fake_redis = FakeRedis()
    monkeypatch.setattr("uvts_api.main.Redis.from_url", lambda *args, **kwargs: fake_redis)
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        redis_url="redis://unused/0",
        document_processing_eager=True,
        auto_create_schema=True,
        session_cookie_secure=False,
        sse_heartbeat_seconds=0.01,
    ).model_copy(update={"storage_root": tmp_path / "documents"})
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as test_client:
        yield test_client
