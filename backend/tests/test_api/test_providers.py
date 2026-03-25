"""Tests for provider endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_providers(client: AsyncClient):
    response = await client.get("/api/v1/providers")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 9
    names = {p["name"] for p in data["providers"]}
    assert "kokoro" in names
    assert "elevenlabs" in names
