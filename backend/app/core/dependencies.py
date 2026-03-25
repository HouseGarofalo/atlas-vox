"""FastAPI dependency injection."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import decode_access_token


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> dict | None:
    """Extract and validate the current user from JWT or API key.

    When AUTH_DISABLED=true, returns a default user dict.
    """
    if settings.auth_disabled:
        return {"sub": "local-user", "scopes": ["admin"]}

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    # Bearer token
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        claims = decode_access_token(token)
        if claims is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        return claims

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authorization scheme",
    )


DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict | None, Depends(get_current_user)]
