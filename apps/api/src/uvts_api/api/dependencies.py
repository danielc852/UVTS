from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from uvts_api.adapters.db.models import AnonymousSession
from uvts_api.core.config import Settings
from uvts_api.core.errors import session_required
from uvts_api.core.security import hash_session_token
from uvts_api.ports.storage import DocumentStorage


def get_runtime_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
RuntimeSettings = Annotated[Settings, Depends(get_runtime_settings)]


def get_document_storage(request: Request) -> DocumentStorage:
    return cast(DocumentStorage, request.app.state.document_storage)


DocumentStorageDependency = Annotated[DocumentStorage, Depends(get_document_storage)]


async def get_current_session(
    request: Request,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> AnonymousSession:
    session_cookie = request.cookies.get(settings.session_cookie_name)
    if not session_cookie:
        raise session_required()
    token_hash = hash_session_token(session_cookie)
    result = await db.execute(
        select(AnonymousSession).where(
            AnonymousSession.token_hash == token_hash,
            AnonymousSession.expires_at > datetime.now(UTC),
        )
    )
    current = result.scalar_one_or_none()
    if current is None:
        raise session_required()
    current.last_seen_at = datetime.now(UTC)
    await db.commit()
    return current


CurrentSession = Annotated[AnonymousSession, Depends(get_current_session)]
