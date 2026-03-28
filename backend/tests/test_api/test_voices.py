"""Tests for voice library endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_all_voices(client: AsyncClient):
    """GET /api/v1/voices returns voices from providers."""
    resp = await client.get("/api/v1/voices")
    assert resp.status_code == 200
    data = resp.json()
    assert "voices" in data
    assert "count" in data
    assert data["count"] >= 0
    assert isinstance(data["voices"], list)


@pytest.mark.asyncio
async def test_list_all_voices_structure(client: AsyncClient):
    """Each voice entry has the expected keys."""
    resp = await client.get("/api/v1/voices")
    assert resp.status_code == 200
    data = resp.json()
    for voice in data["voices"]:
        assert "voice_id" in voice
        assert "name" in voice
        assert "provider" in voice
        assert "provider_display" in voice


@pytest.mark.asyncio
async def test_preview_voice_invalid_provider(client: AsyncClient):
    """POST /api/v1/voices/preview with unknown provider returns 400."""
    resp = await client.post("/api/v1/voices/preview", json={
        "provider": "nonexistent",
        "voice_id": "test",
    })
    assert resp.status_code == 400
    assert "nonexistent" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_preview_voice_missing_fields(client: AsyncClient):
    """POST /api/v1/voices/preview without required fields returns 422."""
    resp = await client.post("/api/v1/voices/preview", json={})
    assert resp.status_code == 422
