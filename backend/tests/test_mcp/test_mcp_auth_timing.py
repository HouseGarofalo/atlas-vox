"""P1-10 regression: MCP auth must run EXACTLY ONE Argon2 verify per request.

Before the fix the handler ran up to 5 verifies when key_prefix collided,
giving an attacker a CPU DoS vector. This test enforces the new contract
by counting the number of verify_api_key calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.mcp.transport import _verify_mcp_auth


@pytest.mark.asyncio
async def test_auth_disabled_bypasses_lookup(monkeypatch):
    monkeypatch.setattr("app.mcp.transport.settings.auth_disabled", True)
    ctx = await _verify_mcp_auth("Bearer irrelevant")
    assert ctx["sub"] == "local-user"
    assert "admin" in ctx["scopes"]


@pytest.mark.asyncio
async def test_missing_authorization_rejected(monkeypatch):
    monkeypatch.setattr("app.mcp.transport.settings.auth_disabled", False)
    with pytest.raises(HTTPException) as exc:
        await _verify_mcp_auth(None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_called_at_most_once_per_request(monkeypatch):
    """Even if the DB returns multiple candidates (unlikely with 12-char
    prefix), we must verify at most ONE so Argon2 CPU usage is bounded.
    """
    monkeypatch.setattr("app.mcp.transport.settings.auth_disabled", False)

    # Simulate a DB result with AT MOST one row (SQL limit(1) in play).
    fake_key = type("K", (), {
        "id": "kid-1",
        "key_hash": "argon2-hash-x",
        "scopes": "read",
    })()

    fake_result = type("R", (), {"scalar_one_or_none": lambda self: fake_key})()

    fake_db = AsyncMock()
    fake_db.execute = AsyncMock(return_value=fake_result)
    fake_db.__aenter__ = AsyncMock(return_value=fake_db)
    fake_db.__aexit__ = AsyncMock(return_value=False)

    verify_mock = AsyncMock(return_value=True)

    with patch("app.core.database.async_session_factory", return_value=fake_db), \
         patch("app.mcp.transport.verify_api_key", verify_mock):
        ctx = await _verify_mcp_auth("Bearer avx_" + "x" * 40)

    assert ctx["sub"] == "kid-1"
    assert verify_mock.call_count == 1  # bounded — never more than one


@pytest.mark.asyncio
async def test_no_matching_prefix_does_not_verify(monkeypatch):
    """When the prefix lookup returns nothing we must NOT call verify at all.

    Saves a ~150ms Argon2 hash on every unauthenticated probe.
    """
    monkeypatch.setattr("app.mcp.transport.settings.auth_disabled", False)

    fake_result = type("R", (), {"scalar_one_or_none": lambda self: None})()
    fake_db = AsyncMock()
    fake_db.execute = AsyncMock(return_value=fake_result)
    fake_db.__aenter__ = AsyncMock(return_value=fake_db)
    fake_db.__aexit__ = AsyncMock(return_value=False)

    verify_mock = AsyncMock()

    with patch("app.core.database.async_session_factory", return_value=fake_db), \
         patch("app.mcp.transport.verify_api_key", verify_mock):
        with pytest.raises(HTTPException) as exc:
            await _verify_mcp_auth("Bearer avx_nomatch")

    assert exc.value.status_code == 401
    assert verify_mock.call_count == 0  # never verified a hash
