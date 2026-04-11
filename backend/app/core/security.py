"""JWT tokens (access + refresh), API key authentication, and token blacklist."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import structlog
from argon2 import PasswordHasher
from jwt.exceptions import ExpiredSignatureError, PyJWTError

from app.core.config import settings

logger = structlog.get_logger(__name__)

ph = PasswordHasher()


# ---------------------------------------------------------------------------
# API key helpers
# ---------------------------------------------------------------------------

def hash_api_key(api_key: str) -> str:
    """Hash an API key using Argon2id."""
    result = ph.hash(api_key)
    logger.debug("api_key_hashed")
    return result


def verify_api_key(api_key: str, hashed: str) -> bool:
    """Verify an API key against its Argon2id hash."""
    try:
        verified = ph.verify(hashed, api_key)
        logger.debug("api_key_verification", success=verified)
        return verified
    except Exception:
        logger.debug("api_key_verification", success=False)
        return False


# ---------------------------------------------------------------------------
# JWT — access tokens
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a short-lived JWT access token.

    Includes a ``jti`` (JWT ID) claim so the token can be individually
    blacklisted, and a ``type`` claim set to ``"access"``.
    """
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + (
        expires_delta or timedelta(minutes=settings.jwt_access_expire_minutes)
    )
    jti = uuid.uuid4().hex
    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": "atlas-vox",
        "jti": jti,
        "type": "access",
    })
    token = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    logger.info(
        "access_token_created",
        subject=data.get("sub"),
        jti=jti,
        expires_at=expire.isoformat(),
    )
    return token


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token.

    Returns the claims dict or ``None`` on any validation failure.
    Rejects tokens whose ``type`` is not ``"access"`` (or missing, for
    backward-compat with pre-typed tokens).
    """
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer="atlas-vox",
        )
        token_type = claims.get("type", "access")  # pre-typed tokens default to access
        if token_type != "access":
            logger.warning("access_token_decode_failed", reason="wrong_type", type=token_type)
            return None
        logger.debug("access_token_decoded", subject=claims.get("sub"))
        return claims
    except ExpiredSignatureError:
        logger.warning("access_token_decode_failed", reason="expired")
        return None
    except PyJWTError as exc:
        logger.warning("access_token_decode_failed", reason="invalid", detail=str(exc))
        return None


# ---------------------------------------------------------------------------
# JWT — refresh tokens
# ---------------------------------------------------------------------------

def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a long-lived JWT refresh token (default 7 days).

    Includes ``type: "refresh"`` and a unique ``jti`` for blacklisting.
    """
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + (
        expires_delta or timedelta(days=settings.jwt_refresh_expire_days)
    )
    jti = uuid.uuid4().hex
    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": "atlas-vox",
        "jti": jti,
        "type": "refresh",
    })
    token = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    logger.info(
        "refresh_token_created",
        subject=data.get("sub"),
        jti=jti,
        expires_at=expire.isoformat(),
    )
    return token


def decode_refresh_token(token: str) -> dict | None:
    """Decode and validate a JWT refresh token.

    Returns the claims dict or ``None``.  Rejects tokens whose ``type``
    is not ``"refresh"``.
    """
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer="atlas-vox",
        )
        if claims.get("type") != "refresh":
            logger.warning("refresh_token_decode_failed", reason="wrong_type", type=claims.get("type"))
            return None
        logger.debug("refresh_token_decoded", subject=claims.get("sub"))
        return claims
    except ExpiredSignatureError:
        logger.warning("refresh_token_decode_failed", reason="expired")
        return None
    except PyJWTError as exc:
        logger.warning("refresh_token_decode_failed", reason="invalid", detail=str(exc))
        return None


# ---------------------------------------------------------------------------
# Token blacklist (Redis-backed)
# ---------------------------------------------------------------------------

async def _get_redis():
    """Return an async Redis client.  Caller is responsible for closing."""
    import redis.asyncio as aioredis

    return aioredis.from_url(settings.redis_url, socket_timeout=3)


async def blacklist_token(jti: str, exp: int | float) -> None:
    """Add a token's JTI to the blacklist in Redis.

    The key is set with a TTL equal to the remaining lifetime of the token
    so entries auto-expire and don't accumulate forever.

    Args:
        jti: The JWT ID claim value.
        exp: The ``exp`` claim (Unix timestamp) from the token.
    """
    remaining = int(exp - datetime.now(UTC).timestamp())
    if remaining <= 0:
        logger.debug("blacklist_skip", jti=jti, reason="already_expired")
        return

    try:
        r = await _get_redis()
        await r.setex(f"token_blacklist:{jti}", remaining, "1")
        await r.aclose()
        logger.info("token_blacklisted", jti=jti, ttl_seconds=remaining)
    except Exception as exc:
        logger.error("blacklist_failed", jti=jti, error=str(exc))


async def is_token_blacklisted(jti: str) -> bool:
    """Check whether a token JTI has been blacklisted."""
    try:
        r = await _get_redis()
        result = await r.exists(f"token_blacklist:{jti}")
        await r.aclose()
        return bool(result)
    except Exception as exc:
        # If Redis is down we fail-open (log it but allow the request).
        # Production deployments should monitor Redis health.
        logger.error("blacklist_check_failed", jti=jti, error=str(exc))
        return False
