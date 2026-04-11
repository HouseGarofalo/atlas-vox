"""Comprehensive tests for auth endpoints — login, refresh, logout, /me, /status.

The default ``client`` fixture from conftest has ``AUTH_DISABLED=true``.
Tests that need real JWT auth create a separate ``auth_client`` fixture that
overrides ``settings.auth_disabled = False`` and crafts proper tokens via
``create_access_token`` / ``create_refresh_token``.
"""

from __future__ import annotations

import time
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_current_user_from_refresh, get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
)
from app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def auth_client(db_session: AsyncSession):
    """Async test client with auth ENABLED.

    Overrides ``settings.auth_disabled`` to ``False`` for the duration of
    the test, then restores the original value.  The JWT secret is already
    set to a known value in the test environment, so tokens created with
    ``create_access_token`` will validate correctly.
    """
    original_auth_disabled = settings.auth_disabled
    original_jwt_secret = settings.jwt_secret_key
    original_encryption_key = settings.encryption_key
    settings.auth_disabled = False
    # Ensure we have a valid JWT secret for tests
    settings.jwt_secret_key = "test-secret-key-for-auth-tests-minimum-32-chars"
    settings.encryption_key = "test-encryption-key-for-auth-tests"

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    settings.auth_disabled = original_auth_disabled
    settings.jwt_secret_key = original_jwt_secret
    settings.encryption_key = original_encryption_key


def _make_auth_header(token: str) -> dict[str, str]:
    """Build an Authorization: Bearer header."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Auth status endpoint
# ---------------------------------------------------------------------------


class TestAuthStatus:
    """GET /api/v1/auth/status — always public."""

    @pytest.mark.asyncio
    async def test_auth_status_disabled(self, client: AsyncClient):
        """When AUTH_DISABLED=true, status reports auth_disabled=true."""
        response = await client.get("/api/v1/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_disabled"] is True

    @pytest.mark.asyncio
    async def test_auth_status_enabled(self, auth_client: AsyncClient):
        """When auth is enabled, status reports auth_disabled=false."""
        response = await auth_client.get("/api/v1/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_disabled"] is False


# ---------------------------------------------------------------------------
# 2. Login flow
# ---------------------------------------------------------------------------


class TestLogin:
    """POST /api/v1/auth/login."""

    @pytest.mark.asyncio
    async def test_login_auth_disabled_returns_tokens(self, client: AsyncClient):
        """With AUTH_DISABLED=true, login hands back tokens for local-user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_auth_disabled_sets_refresh_cookie(self, client: AsyncClient):
        """With AUTH_DISABLED=true, login sets an httpOnly refresh cookie."""
        response = await client.post(
            "/api/v1/auth/login",
            json={},
        )
        assert response.status_code == 200
        # The response should include a Set-Cookie header for refresh_token
        cookies = response.headers.get_list("set-cookie")
        refresh_cookies = [c for c in cookies if "refresh_token" in c]
        assert len(refresh_cookies) >= 1
        cookie = refresh_cookies[0]
        assert "httponly" in cookie.lower()
        assert "path=/api/v1/auth" in cookie.lower()

    @pytest.mark.asyncio
    async def test_login_no_credentials_returns_400(self, auth_client: AsyncClient):
        """With auth enabled and no credentials provided, returns 400."""
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={},
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_login_invalid_api_key_returns_401(self, auth_client: AsyncClient):
        """With auth enabled and an invalid API key, returns 401."""
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={"api_key": "avx_invalid_key_value"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid API key"

    @pytest.mark.asyncio
    async def test_login_email_password_returns_501(self, auth_client: AsyncClient):
        """Email/password login is not yet implemented — returns 501."""
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "secret"},
        )
        assert response.status_code == 501
        data = response.json()
        assert "not yet implemented" in data["detail"].lower()


# ---------------------------------------------------------------------------
# 3. Token validation — GET /auth/me
# ---------------------------------------------------------------------------


class TestGetMe:
    """GET /api/v1/auth/me — returns user claims."""

    @pytest.mark.asyncio
    async def test_me_auth_disabled(self, client: AsyncClient):
        """With AUTH_DISABLED=true, /me returns the default local-user."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["sub"] == "local-user"
        assert "admin" in data["scopes"]

    @pytest.mark.asyncio
    async def test_me_with_valid_token(self, auth_client: AsyncClient):
        """With a valid access token, /me returns the user claims."""
        token = create_access_token(
            {"sub": "test-user", "scopes": ["read", "write"]},
        )
        response = await auth_client.get(
            "/api/v1/auth/me",
            headers=_make_auth_header(token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sub"] == "test-user"
        assert "read" in data["scopes"]
        assert "write" in data["scopes"]
        assert data["token_type"] == "access"

    @pytest.mark.asyncio
    async def test_me_without_token_returns_401(self, auth_client: AsyncClient):
        """Without an Authorization header, /me returns 401."""
        response = await auth_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_invalid_token_returns_401(self, auth_client: AsyncClient):
        """With a malformed/invalid token, /me returns 401."""
        response = await auth_client.get(
            "/api/v1/auth/me",
            headers=_make_auth_header("not.a.valid.jwt"),
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_bad_scheme_returns_401(self, auth_client: AsyncClient):
        """Using 'Basic' instead of 'Bearer' returns 401."""
        token = create_access_token({"sub": "test-user", "scopes": ["read"]})
        response = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Basic {token}"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 4. Token expiry
# ---------------------------------------------------------------------------


class TestTokenExpiry:
    """Expired tokens should be rejected with 401."""

    @pytest.mark.asyncio
    async def test_expired_access_token_returns_401(self, auth_client: AsyncClient):
        """An access token created with a past expiry is rejected."""
        token = create_access_token(
            {"sub": "test-user", "scopes": ["read"]},
            expires_delta=timedelta(seconds=-1),
        )
        response = await auth_client.get(
            "/api/v1/auth/me",
            headers=_make_auth_header(token),
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 5. Refresh token flow
# ---------------------------------------------------------------------------


class TestRefreshToken:
    """POST /api/v1/auth/refresh — rotate tokens via refresh cookie."""

    @pytest.mark.asyncio
    @patch("app.core.dependencies.is_token_blacklisted", new_callable=AsyncMock, return_value=False)
    @patch("app.api.v1.endpoints.auth.blacklist_token", new_callable=AsyncMock)
    async def test_refresh_with_valid_cookie(
        self,
        mock_blacklist: AsyncMock,
        mock_is_blacklisted: AsyncMock,
        auth_client: AsyncClient,
    ):
        """A valid refresh cookie yields a new access token and rotated cookie."""
        refresh = create_refresh_token(
            {"sub": "test-user", "scopes": ["read"]},
        )
        # Send the refresh token as a cookie
        auth_client.cookies.set("refresh_token", refresh)
        response = await auth_client.post("/api/v1/auth/refresh")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

        # Should have blacklisted the old refresh token
        mock_blacklist.assert_called_once()

        # New refresh cookie should be set
        cookies = response.headers.get_list("set-cookie")
        refresh_cookies = [c for c in cookies if "refresh_token" in c]
        assert len(refresh_cookies) >= 1

    @pytest.mark.asyncio
    async def test_refresh_without_cookie_returns_401(self, auth_client: AsyncClient):
        """Without a refresh_token cookie, /refresh returns 401."""
        response = await auth_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_expired_cookie_returns_401(self, auth_client: AsyncClient):
        """An expired refresh token cookie returns 401."""
        refresh = create_refresh_token(
            {"sub": "test-user", "scopes": ["read"]},
            expires_delta=timedelta(seconds=-1),
        )
        auth_client.cookies.set("refresh_token", refresh)
        response = await auth_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_cookie_returns_401(self, auth_client: AsyncClient):
        """Using an access token (type=access) as the refresh cookie fails."""
        # An access token has type="access", refresh endpoint expects type="refresh"
        access = create_access_token(
            {"sub": "test-user", "scopes": ["read"]},
        )
        auth_client.cookies.set("refresh_token", access)
        response = await auth_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("app.core.dependencies.is_token_blacklisted", new_callable=AsyncMock, return_value=True)
    async def test_refresh_blacklisted_token_returns_401(
        self,
        mock_is_blacklisted: AsyncMock,
        auth_client: AsyncClient,
    ):
        """A blacklisted refresh token is rejected."""
        refresh = create_refresh_token(
            {"sub": "test-user", "scopes": ["read"]},
        )
        auth_client.cookies.set("refresh_token", refresh)
        response = await auth_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 6. Logout
# ---------------------------------------------------------------------------


class TestLogout:
    """POST /api/v1/auth/logout — blacklist token and clear cookie."""

    @pytest.mark.asyncio
    @patch("app.core.dependencies.is_token_blacklisted", new_callable=AsyncMock, return_value=False)
    @patch("app.api.v1.endpoints.auth.blacklist_token", new_callable=AsyncMock)
    async def test_logout_blacklists_token(
        self,
        mock_blacklist: AsyncMock,
        mock_is_blacklisted: AsyncMock,
        auth_client: AsyncClient,
    ):
        """Logout blacklists the access token and clears the refresh cookie."""
        token = create_access_token(
            {"sub": "test-user", "scopes": ["read"]},
        )
        response = await auth_client.post(
            "/api/v1/auth/logout",
            headers=_make_auth_header(token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["detail"] == "Logged out"

        # The access token's jti should have been blacklisted
        mock_blacklist.assert_called_once()
        # Verify the jti passed matches the token's jti
        claims = decode_access_token(token)
        assert claims is not None
        call_args = mock_blacklist.call_args
        assert call_args[0][0] == claims["jti"]  # first positional arg = jti

    @pytest.mark.asyncio
    async def test_logout_without_token_returns_401(self, auth_client: AsyncClient):
        """Logout without a token returns 401."""
        response = await auth_client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_auth_disabled(self, client: AsyncClient):
        """When AUTH_DISABLED=true, logout still works for the local user."""
        response = await client.post("/api/v1/auth/logout")
        # With auth disabled, the dependency returns a default user (no jti/exp),
        # so blacklisting is skipped but the endpoint succeeds.
        assert response.status_code == 200
        data = response.json()
        assert data["detail"] == "Logged out"


# ---------------------------------------------------------------------------
# 7. Blacklisted token rejection
# ---------------------------------------------------------------------------


class TestBlacklistedToken:
    """Blacklisted tokens should be rejected at the dependency level."""

    @pytest.mark.asyncio
    @patch("app.core.dependencies.is_token_blacklisted", new_callable=AsyncMock, return_value=True)
    async def test_blacklisted_access_token_rejected(
        self,
        mock_is_blacklisted: AsyncMock,
        auth_client: AsyncClient,
    ):
        """A blacklisted access token returns 401 on /me."""
        token = create_access_token(
            {"sub": "test-user", "scopes": ["read"]},
        )
        response = await auth_client.get(
            "/api/v1/auth/me",
            headers=_make_auth_header(token),
        )
        assert response.status_code == 401
        data = response.json()
        assert "revoked" in data["detail"].lower()


# ---------------------------------------------------------------------------
# 8. Scope enforcement
# ---------------------------------------------------------------------------


class TestScopeEnforcement:
    """Scope-based access control via require_scope dependency."""

    @pytest.mark.asyncio
    @patch("app.core.dependencies.is_token_blacklisted", new_callable=AsyncMock, return_value=False)
    async def test_admin_scope_accesses_admin_endpoint(
        self,
        mock_is_blacklisted: AsyncMock,
        auth_client: AsyncClient,
    ):
        """A token with admin scope can access admin-only endpoints."""
        token = create_access_token(
            {"sub": "admin-user", "scopes": ["admin"]},
        )
        # GET /api/v1/admin/system-info requires require_scope("admin")
        response = await auth_client.get(
            "/api/v1/admin/system-info",
            headers=_make_auth_header(token),
        )
        # Admin endpoint should succeed (200)
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("app.core.dependencies.is_token_blacklisted", new_callable=AsyncMock, return_value=False)
    async def test_non_admin_scope_denied_admin_endpoint(
        self,
        mock_is_blacklisted: AsyncMock,
        auth_client: AsyncClient,
    ):
        """A token with only 'read' scope cannot access admin-only endpoints."""
        token = create_access_token(
            {"sub": "reader-user", "scopes": ["read"]},
        )
        # Seed settings first so the endpoint doesn't 404
        admin_token = create_access_token(
            {"sub": "admin-user", "scopes": ["admin"]},
        )
        await auth_client.post(
            "/api/v1/admin/settings/seed",
            headers=_make_auth_header(admin_token),
        )
        # Now try to access with limited scopes
        response = await auth_client.get(
            "/api/v1/admin/settings",
            headers=_make_auth_header(token),
        )
        assert response.status_code == 403
        data = response.json()
        assert "scope" in data["detail"].lower()


# ---------------------------------------------------------------------------
# 9. Token decode edge cases
# ---------------------------------------------------------------------------


class TestTokenDecode:
    """Unit-level tests for token creation / decoding logic."""

    def test_access_token_roundtrip(self):
        """create_access_token -> decode_access_token returns matching claims."""
        token = create_access_token(
            {"sub": "unit-test", "scopes": ["read"]},
        )
        claims = decode_access_token(token)
        assert claims is not None
        assert claims["sub"] == "unit-test"
        assert claims["scopes"] == ["read"]
        assert claims["type"] == "access"
        assert "jti" in claims
        assert "exp" in claims
        assert "iat" in claims
        assert claims["iss"] == "atlas-vox"

    def test_refresh_token_rejected_by_access_decoder(self):
        """A refresh token cannot be decoded as an access token."""
        refresh = create_refresh_token(
            {"sub": "unit-test", "scopes": ["read"]},
        )
        result = decode_access_token(refresh)
        assert result is None

    def test_access_token_has_unique_jti(self):
        """Each token gets a unique jti."""
        t1 = create_access_token({"sub": "a", "scopes": []})
        t2 = create_access_token({"sub": "a", "scopes": []})
        c1 = decode_access_token(t1)
        c2 = decode_access_token(t2)
        assert c1 is not None and c2 is not None
        assert c1["jti"] != c2["jti"]


# ---------------------------------------------------------------------------
# 10. Full login -> use -> logout flow (auth disabled)
# ---------------------------------------------------------------------------


class TestFullFlowAuthDisabled:
    """End-to-end flow with AUTH_DISABLED=true."""

    @pytest.mark.asyncio
    async def test_login_use_logout_flow(self, client: AsyncClient):
        """Login -> /me -> logout -> verify logout all work in sequence."""
        # Step 1: Login
        login_resp = await client.post("/api/v1/auth/login", json={})
        assert login_resp.status_code == 200
        access_token = login_resp.json()["access_token"]
        assert access_token

        # Step 2: Use the token to hit /me
        me_resp = await client.get("/api/v1/auth/me")
        assert me_resp.status_code == 200
        assert me_resp.json()["sub"] == "local-user"

        # Step 3: Check status
        status_resp = await client.get("/api/v1/auth/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["auth_disabled"] is True

        # Step 4: Logout
        logout_resp = await client.post("/api/v1/auth/logout")
        assert logout_resp.status_code == 200
        assert logout_resp.json()["detail"] == "Logged out"
