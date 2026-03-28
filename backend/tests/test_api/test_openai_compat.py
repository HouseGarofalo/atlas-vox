"""Tests for OpenAI-compatible TTS endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_models(client: AsyncClient):
    """GET /v1/models returns OpenAI-format model list."""
    resp = await client.get("/v1/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"
    assert len(data["data"]) > 0
    assert data["data"][0]["object"] == "model"


@pytest.mark.asyncio
async def test_list_models_includes_tts1(client: AsyncClient):
    """The models list includes the tts-1 alias."""
    resp = await client.get("/v1/models")
    data = resp.json()
    ids = {m["id"] for m in data["data"]}
    assert "tts-1" in ids
    assert "tts-1-hd" in ids


@pytest.mark.asyncio
async def test_list_models_owned_by(client: AsyncClient):
    """All models are owned by atlas-vox."""
    resp = await client.get("/v1/models")
    data = resp.json()
    for model in data["data"]:
        assert model["owned_by"] == "atlas-vox"


@pytest.mark.asyncio
async def test_speech_invalid_provider(client: AsyncClient):
    """POST /v1/audio/speech with unknown model and non-mapped voice returns 400."""
    # Use a voice NOT in OPENAI_VOICE_MAP so the model resolves directly to provider
    resp = await client.post("/v1/audio/speech", json={
        "model": "nonexistent_provider",
        "input": "test",
        "voice": "custom_voice_xyz",
    })
    assert resp.status_code == 400
    assert "nonexistent_provider" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_speech_missing_input(client: AsyncClient):
    """POST /v1/audio/speech without input returns 422."""
    resp = await client.post("/v1/audio/speech", json={
        "model": "tts-1",
        "voice": "alloy",
    })
    assert resp.status_code == 422
