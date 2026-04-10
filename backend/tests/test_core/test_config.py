"""Tests for application configuration."""

from __future__ import annotations

import pytest


def test_default_debug_is_false():
    """debug defaults to False."""
    from app.core.config import Settings
    s = Settings(database_url="sqlite+aiosqlite:///test.db")
    assert s.debug is False


def test_jwt_secret_rejected_when_auth_enabled():
    """Raises ValueError when auth_disabled=False and JWT secret is default."""
    from app.core.config import Settings
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(
            auth_disabled=False,
            jwt_secret_key="change-me-in-production",
            database_url="sqlite+aiosqlite:///test.db",
        )


def test_jwt_secret_accepted_when_auth_disabled():
    """No error when auth_disabled=True even with default secret."""
    from app.core.config import Settings
    s = Settings(
        auth_disabled=True,
        jwt_secret_key="change-me-in-production",
        database_url="sqlite+aiosqlite:///test.db",
    )
    assert s.auth_disabled is True


def test_jwt_secret_accepted_with_custom_key():
    """No error when custom JWT secret is provided."""
    from app.core.config import Settings
    s = Settings(
        auth_disabled=False,
        jwt_secret_key="my-super-secure-random-key-12345",
        encryption_key="another-secure-key-for-encryption-12345",
        database_url="sqlite+aiosqlite:///test.db",
    )
    assert s.jwt_secret_key == "my-super-secure-random-key-12345"
