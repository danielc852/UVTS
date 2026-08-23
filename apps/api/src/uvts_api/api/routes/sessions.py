from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from uvts_api.adapters.db.models import AnonymousSession
from uvts_api.api.dependencies import DatabaseSession, RuntimeSettings
from uvts_api.core.security import generate_session_token, hash_session_token
from uvts_api.schemas.sessions import SessionBootstrapResponse

router = APIRouter(prefix="/session", tags=["session"])


@router.post("", response_model=SessionBootstrapResponse)
async def bootstrap_session(
    request: Request,
    response: Response,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> SessionBootstrapResponse:
    cookie = request.cookies.get(settings.session_cookie_name)
    if cookie:
        current = await db.scalar(
            select(AnonymousSession).where(
                AnonymousSession.token_hash == hash_session_token(cookie),
                AnonymousSession.expires_at > datetime.now(UTC),
            )
        )
        if current is not None:
            now = datetime.now(UTC)
            current.last_seen_at = now
            await db.commit()
            expires_at = current.expires_at
            if expires_at.tzinfo is None:  # SQLite test/dev compatibility.
                expires_at = expires_at.replace(tzinfo=UTC)
            return SessionBootstrapResponse(
                expires_in_seconds=max(0, int((expires_at - now).total_seconds()))
            )
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.session_ttl_seconds)
    while True:
        token = generate_session_token()
        token_hash = hash_session_token(token)
        existing = await db.scalar(
            select(AnonymousSession).where(AnonymousSession.token_hash == token_hash)
        )
        if existing is None:
            break
    db.add(AnonymousSession(token_hash=token_hash, expires_at=expires_at))
    await db.commit()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return SessionBootstrapResponse(expires_in_seconds=settings.session_ttl_seconds)
