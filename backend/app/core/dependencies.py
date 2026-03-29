"""FastAPI dependency injection."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

import structlog
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import decode_access_token

logger = structlog.get_logger(__name__)


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
        logger.debug("auth_bypass", reason="AUTH_DISABLED")
        return {"sub": "local-user", "scopes": ["admin"]}

    if not authorization:
        logger.warning("auth_failed", reason="missing_authorization_header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    # Bearer token
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        claims = decode_access_token(token)
        if claims is None:
            logger.warning("auth_failed", reason="invalid_or_expired_token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        return claims

    logger.warning("auth_failed", reason="invalid_authorization_scheme")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authorization scheme",
    )


DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict | None, Depends(get_current_user)]


def require_scope(*scopes: str):
    """Create a dependency that enforces the user has at least one of the given scopes.

    When AUTH_DISABLED=true the user is injected as an admin (all scopes pass).
    When auth is enabled, 'admin' scope bypasses all checks; otherwise the user
    must hold at least one of the specified scopes.

    Usage::

        @router.post("/train")
        async def train(user: Annotated[dict, require_scope("train")]):
            ...
    """
    async def _check(user: CurrentUser) -> dict:
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        user_scopes = user.get("scopes", [])
        if "admin" in user_scopes:
            return user  # admin bypasses scope checks
        if not any(s in user_scopes for s in scopes):
            logger.warning(
                "scope_denied",
                required_scopes=list(scopes),
                user_scopes=user_scopes,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required scope: {' or '.join(scopes)}",
            )
        return user
    return Depends(_check)


# Convenience alias — use as a type annotation in endpoint signatures
RequireScope = require_scope
