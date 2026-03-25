"""JWT tokens and API key authentication."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from jose import JWTError, jwt

from app.core.config import settings

ph = PasswordHasher()


def hash_api_key(api_key: str) -> str:
    """Hash an API key using Argon2id."""
    return ph.hash(api_key)


def verify_api_key(api_key: str, hashed: str) -> bool:
    """Verify an API key against its Argon2id hash."""
    try:
        return ph.verify(hashed, api_key)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns claims or None."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
