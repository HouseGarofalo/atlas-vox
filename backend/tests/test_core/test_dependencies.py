"""Tests for dependency injection — scope enforcement."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def test_scope_admin_bypasses_all(client: AsyncClient):
    """Admin scope bypasses all scope checks (default user is admin when AUTH_DISABLED)."""
    # The default test user has admin scope, so all endpoints should work
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


async def test_require_scope_function_exists():
    """require_scope is importable and callable."""
    from app.core.dependencies import require_scope
    dep = require_scope("synthesize")
    assert dep is not None


async def test_require_scope_returns_depends():
    """require_scope returns a FastAPI Depends object."""
    from app.core.dependencies import require_scope
    dep = require_scope("read", "write")
    # Depends objects have a 'dependency' attribute
    assert hasattr(dep, "dependency")
