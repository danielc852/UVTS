from fastapi import FastAPI
from httpx import AsyncClient


async def test_live_and_ready(client: AsyncClient) -> None:
    live = await client.get("/api/v1/health/live")
    ready = await client.get("/api/v1/health/ready")

    assert live.json() == {"status": "live"}
    assert ready.json() == {"status": "ready", "database": "ok", "redis": "ok"}


async def test_ready_uses_stable_error_when_redis_is_down(
    app: FastAPI, client: AsyncClient
) -> None:
    app.state.redis.available = False

    response = await client.get("/api/v1/health/ready", headers={"X-Request-ID": "ready-1"})

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "dependencies_unavailable",
            "message": "UVTS is not ready yet.",
            "retryable": True,
            "field_errors": None,
            "details": {"unavailable": ["redis"]},
        },
        "request_id": "ready-1",
    }
