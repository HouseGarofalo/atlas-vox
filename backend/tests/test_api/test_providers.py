"""Tests for provider endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_providers(client: AsyncClient):
    response = await client.get("/api/v1/providers")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 9  # 9 local/cloud + GPU providers if service running
    names = {p["name"] for p in data["providers"]}
    assert "kokoro" in names
    assert "elevenlabs" in names


@pytest.mark.asyncio
async def test_get_provider_known(client: AsyncClient):
    """GET /api/v1/providers/kokoro returns 200 with provider details."""
    response = await client.get("/api/v1/providers/kokoro")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "kokoro"
    assert "display_name" in data
    assert "provider_type" in data
    assert "enabled" in data
    assert "gpu_mode" in data


@pytest.mark.asyncio
async def test_get_provider_unknown(client: AsyncClient):
    """GET /api/v1/providers/nonexistent returns 404."""
    response = await client.get("/api/v1/providers/nonexistent")
    assert response.status_code == 404
    assert "nonexistent" in response.json()["detail"].lower() or "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_check_provider_health(client: AsyncClient):
    """POST /api/v1/providers/kokoro/health returns a health status."""
    response = await client.post("/api/v1/providers/kokoro/health")
    assert response.status_code == 200
    data = response.json()
    assert "healthy" in data
    assert "name" in data
    assert data["name"] == "kokoro"
    assert isinstance(data["healthy"], bool)


@pytest.mark.asyncio
async def test_check_provider_health_unknown(client: AsyncClient):
    """POST /api/v1/providers/nonexistent/health returns 404."""
    response = await client.post("/api/v1/providers/nonexistent/health")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_provider_voices(client: AsyncClient):
    """GET /api/v1/providers/kokoro/voices returns voice list."""
    response = await client.get("/api/v1/providers/kokoro/voices")
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert data["provider"] == "kokoro"
    assert "voices" in data
    assert "count" in data
    assert isinstance(data["voices"], list)
    assert data["count"] == len(data["voices"])
    if data["voices"]:
        voice = data["voices"][0]
        assert "voice_id" in voice
        assert "name" in voice


@pytest.mark.asyncio
async def test_list_provider_voices_unknown(client: AsyncClient):
    """GET /api/v1/providers/nonexistent/voices returns 404."""
    response = await client.get("/api/v1/providers/nonexistent/voices")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_provider_config(client: AsyncClient):
    """GET /api/v1/providers/kokoro/config returns config with schema."""
    response = await client.get("/api/v1/providers/kokoro/config")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "gpu_mode" in data
    assert "config" in data
    assert "config_schema" in data
    assert isinstance(data["config_schema"], list)


@pytest.mark.asyncio
async def test_get_provider_config_unknown(client: AsyncClient):
    """GET /api/v1/providers/nonexistent/config returns 404."""
    response = await client.get("/api/v1/providers/nonexistent/config")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_provider_config(client: AsyncClient):
    """PUT /api/v1/providers/kokoro/config with valid body returns updated config."""
    response = await client.put(
        "/api/v1/providers/kokoro/config",
        json={"enabled": True, "gpu_mode": "none"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "gpu_mode" in data
    assert "config" in data
    assert "config_schema" in data


@pytest.mark.asyncio
async def test_update_provider_config_unknown(client: AsyncClient):
    """PUT /api/v1/providers/nonexistent/config returns 404."""
    response = await client.put(
        "/api/v1/providers/nonexistent/config",
        json={"enabled": True},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_test_provider(client: AsyncClient):
    """POST /api/v1/providers/kokoro/test with mocked synthesize returns test result."""
    from app.providers.base import AudioResult
    from pathlib import Path
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    mock_result = MagicMock(spec=AudioResult)
    mock_result.audio_path = tmp_path
    mock_result.duration_seconds = 1.0

    with patch(
        "app.services.provider_registry.provider_registry.get_provider"
    ) as mock_get:
        mock_provider = AsyncMock()
        mock_provider.list_voices = AsyncMock(return_value=[])
        mock_provider.synthesize = AsyncMock(return_value=mock_result)
        mock_get.return_value = mock_provider

        response = await client.post(
            "/api/v1/providers/kokoro/test",
            json={"text": "Hello world"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "latency_ms" in data


@pytest.mark.asyncio
async def test_test_provider_unknown(client: AsyncClient):
    """POST /api/v1/providers/nonexistent/test returns 404."""
    response = await client.post(
        "/api/v1/providers/nonexistent/test",
        json={"text": "Hello world"},
    )
    assert response.status_code == 404
