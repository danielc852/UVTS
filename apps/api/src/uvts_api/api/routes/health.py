from fastapi import APIRouter, Request
from sqlalchemy import text

from uvts_api.core.errors import AppError
from uvts_api.schemas.errors import ErrorResponse
from uvts_api.schemas.health import LiveResponse, ReadyResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=LiveResponse)
async def live() -> LiveResponse:
    return LiveResponse()


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses={503: {"model": ErrorResponse}},
)
async def ready(request: Request) -> ReadyResponse:
    failures: list[str] = []
    try:
        async with request.app.state.session_factory() as db:
            await db.execute(text("SELECT 1"))
    except Exception:  # Readiness intentionally converts dependency errors to a stable response.
        failures.append("database")
    try:
        await request.app.state.redis.ping()
    except Exception:
        failures.append("redis")
    if failures:
        raise AppError(
            status_code=503,
            code="dependencies_unavailable",
            message="UVTS is not ready yet.",
            retryable=True,
            details={"unavailable": failures},
        )
    return ReadyResponse()
