"""Authentication endpoints — login, refresh, logout, status, and user info."""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.dependencies import CurrentUser, RefreshUser
from app.core.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    dummy_verify_api_key,
    verify_api_key,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["auth"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Login credentials.

    For simple single-user / API-key-based setups the ``api_key`` field
    can be used instead of email + password.  When an API key starting
    with ``avx_`` is supplied, it is validated against the database and
    a JWT pair is returned.
    """

    email: str | None = None
    password: str | None = None
    api_key: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_refresh_cookie(response: JSONResponse, refresh_token: str) -> None:
    """Set the refresh token as an httpOnly cookie on *response*."""
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # Only over HTTPS
        samesite="lax",
        max_age=settings.jwt_refresh_expire_days * 24 * 60 * 60,
        path="/api/v1/auth",  # Only sent to auth endpoints
    )


def _clear_refresh_cookie(response: JSONResponse) -> None:
    """Delete the refresh token cookie."""
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/v1/auth",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/auth/status")
async def auth_status() -> dict:
    """Return whether authentication is enabled or disabled.

    This endpoint is always public so the frontend can determine
    whether to show the login screen or auto-authenticate.
    """
    return {"auth_disabled": settings.auth_disabled}


@router.post("/auth/login")
async def login(body: LoginRequest, request: Request) -> JSONResponse:
    """Authenticate and return an access token + set refresh cookie.

    Supports two flows:

    1. **API key login** — supply ``api_key`` (``avx_…``).  The key is
       validated against the database and a JWT pair is returned.
    2. **Email / password** — (placeholder for future user-model auth).
       Currently returns 501 if no API key is supplied.

    The access token is returned in the JSON body.  The refresh token is
    set as an httpOnly cookie scoped to ``/api/v1/auth``.
    """
    if settings.auth_disabled:
        # When auth is disabled, hand back a token for the default local user
        access = create_access_token({"sub": "local-user", "scopes": ["admin"]})
        refresh = create_refresh_token({"sub": "local-user", "scopes": ["admin"]})
        resp = JSONResponse(
            content={
                "access_token": access,
                "token_type": "bearer",
                "expires_in": settings.jwt_access_expire_minutes * 60,
            }
        )
        _set_refresh_cookie(resp, refresh)
        return resp

    # ---- API key login flow ----
    if body.api_key and body.api_key.startswith("avx_"):
        from sqlalchemy import select

        from app.core.database import async_session_factory
        from app.models.api_key import ApiKey

        prefix = body.api_key[:12]
        async with async_session_factory() as session:
            result = await session.execute(
                select(ApiKey).where(
                    ApiKey.key_prefix == prefix,
                    ApiKey.active.is_(True),
                ).limit(5)
            )
            candidates = result.scalars().all()

            for key_row in candidates:
                if verify_api_key(body.api_key, key_row.key_hash):
                    scopes = [s.strip() for s in key_row.scopes.split(",") if s.strip()]
                    sub = f"api-key:{key_row.id}"
                    access = create_access_token({"sub": sub, "scopes": scopes})
                    refresh = create_refresh_token({"sub": sub, "scopes": scopes})

                    logger.info("login_success", method="api_key", sub=sub)
                    resp = JSONResponse(
                        content={
                            "access_token": access,
                            "token_type": "bearer",
                            "expires_in": settings.jwt_access_expire_minutes * 60,
                        }
                    )
                    _set_refresh_cookie(resp, refresh)
                    return resp

        # Equalise timing: when no candidates matched the prefix, spend the
        # same Argon2 work as a "wrong key for existing prefix" path would,
        # so an attacker cannot distinguish "no such prefix" from
        # "prefix exists but wrong secret" via response latency.
        if not candidates:
            dummy_verify_api_key()

        logger.warning("login_failed", method="api_key", reason="invalid_key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # ---- Email / password flow (placeholder) ----
    if body.email and body.password:
        # TODO: Implement user model lookup + Argon2id password verification.
        # For now, return 501 to signal this flow is not yet wired up.
        logger.warning("login_failed", method="email", reason="not_implemented")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Email/password login is not yet implemented. Use an API key.",
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide either 'api_key' or both 'email' and 'password'.",
    )


@router.post("/auth/refresh")
async def refresh_token(user: RefreshUser, request: Request) -> JSONResponse:
    """Issue a new access token using a valid refresh token cookie.

    Also rotates the refresh token (old one is blacklisted).
    """
    sub = user.get("sub", "unknown")
    scopes = user.get("scopes", [])

    # Blacklist the old refresh token so it can't be reused
    old_jti = user.get("jti")
    old_exp = user.get("exp")
    if old_jti and old_exp:
        await blacklist_token(old_jti, old_exp)

    # Issue new pair
    access = create_access_token({"sub": sub, "scopes": scopes})
    refresh = create_refresh_token({"sub": sub, "scopes": scopes})

    logger.info("token_refreshed", sub=sub)
    resp = JSONResponse(
        content={
            "access_token": access,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_expire_minutes * 60,
        }
    )
    _set_refresh_cookie(resp, refresh)
    return resp


@router.post("/auth/logout")
async def logout(
    user: CurrentUser,
    request: Request,
) -> JSONResponse:
    """Blacklist the current access token and clear the refresh cookie.

    The access token's ``jti`` is added to the Redis blacklist with a
    TTL matching its remaining lifetime, so it cannot be reused.
    """
    if user and user.get("jti") and user.get("exp"):
        await blacklist_token(user["jti"], user["exp"])
        logger.info("logout", sub=user.get("sub"), jti=user.get("jti"))

    resp = JSONResponse(content={"detail": "Logged out"})
    _clear_refresh_cookie(resp)
    return resp


@router.get("/auth/me")
async def get_me(user: CurrentUser) -> dict:
    """Return the current authenticated user's claims.

    Useful for the frontend to display user info and available scopes.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return {
        "sub": user.get("sub"),
        "scopes": user.get("scopes", []),
        "token_type": user.get("type", "access"),
    }
