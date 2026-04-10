"""JWT tokens and API key authentication."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import structlog
from argon2 import PasswordHasher
from jwt.exceptions import ExpiredSignatureError, PyJWTError

from app.core.config import settings

logger = structlog.get_logger(__name__)

ph = PasswordHasher()


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


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": "atlas-vox"
    })
    token = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    logger.info(
        "access_token_created",
        subject=data.get("sub"),
        expires_at=expire.isoformat(),
    )
    return token


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns claims or None."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer="atlas-vox"
        )
        logger.debug("access_token_decoded", subject=claims.get("sub"))
        return claims
    except ExpiredSignatureError:
        logger.warning("access_token_decode_failed", reason="expired")
        return None
    except PyJWTError as exc:
        logger.warning("access_token_decode_failed", reason="invalid", detail=str(exc))
        return None
