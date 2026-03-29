"""Tests for voice library endpoints."""

from __future__ import annotations

import hashlib
import struct
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.config import settings


def _make_wav_bytes() -> bytes:
    """Build a minimal valid WAV file (1 second, mono, 22050 Hz)."""
    sample_rate = 22050
    num_channels = 1
    bits_per_sample = 16
    num_samples = sample_rate
    data_size = num_samples * num_channels * (bits_per_sample // 8)
    chunk_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ",
        16, 1, num_channels, sample_rate,
        sample_rate * num_channels * (bits_per_sample // 8),
        num_channels * (bits_per_sample // 8),
        bits_per_sample, b"data", data_size,
    )
    samples = struct.pack(f"<{num_samples}h", *([0] * num_samples))
    return header + samples


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


@pytest.mark.asyncio
async def test_preview_voice_success(client: AsyncClient, tmp_path: Path):
    """POST /api/v1/voices/preview synthesizes and returns an audio URL."""
    from app.providers.base import AudioResult

    # Write a real WAV file that the mock will return
    wav_file = tmp_path / "preview_test.wav"
    wav_file.write_bytes(_make_wav_bytes())

    mock_audio = MagicMock(spec=AudioResult)
    mock_audio.audio_path = wav_file
    mock_audio.duration_seconds = 1.0

    mock_provider = AsyncMock()
    mock_provider.synthesize = AsyncMock(return_value=mock_audio)

    with patch(
        "app.api.v1.endpoints.voices.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        resp = await client.post("/api/v1/voices/preview", json={
            "provider": "kokoro",
            "voice_id": "af_heart",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "audio_url" in data
    assert "previews" in data["audio_url"]


@pytest.mark.asyncio
async def test_preview_voice_cache_hit(client: AsyncClient):
    """Requesting a preview that already exists returns the cached URL without re-synthesizing."""
    provider = "kokoro"
    voice_id = "af_cache_test"
    text = "Hello, this is a preview of my voice."

    # Pre-create the expected cache file
    key = f"{provider}_{voice_id}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
    preview_dir = Path(settings.storage_path) / "output" / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_file = preview_dir / f"{key}.wav"
    preview_file.write_bytes(_make_wav_bytes())

    try:
        # No mock needed — the endpoint should return the cached file immediately
        resp = await client.post("/api/v1/voices/preview", json={
            "provider": provider,
            "voice_id": voice_id,
        })

        assert resp.status_code == 200
        data = resp.json()
        assert "audio_url" in data
        assert key in data["audio_url"]
    finally:
        # Clean up the preview file we created
        preview_file.unlink(missing_ok=True)
