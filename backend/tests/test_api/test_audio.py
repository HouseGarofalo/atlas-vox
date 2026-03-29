"""Tests for audio file serving endpoints."""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.config import settings


def _make_wav_bytes() -> bytes:
    """Build a minimal valid WAV file in memory."""
    sample_rate = 22050
    num_channels = 1
    bits_per_sample = 16
    num_samples = sample_rate
    data_size = num_samples * num_channels * (bits_per_sample // 8)
    chunk_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE",
        b"fmt ", 16, 1, num_channels, sample_rate,
        sample_rate * num_channels * (bits_per_sample // 8),
        num_channels * (bits_per_sample // 8), bits_per_sample,
        b"data", data_size,
    )
    return header + struct.pack(f"<{num_samples}h", *([0] * num_samples))


# ---------------------------------------------------------------------------
# Not-found paths
# ---------------------------------------------------------------------------

async def test_serve_audio_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/audio/definitely-does-not-exist.wav")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_serve_preview_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/audio/previews/does-not-exist.wav")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Happy path — serve a real file
# ---------------------------------------------------------------------------

async def test_serve_audio_success(client: AsyncClient, tmp_path: Path):
    """Create a real WAV file in the output directory and verify it's served."""
    output_dir = Path(settings.storage_path) / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = "test_serve_fixture.wav"
    wav_path = output_dir / filename
    wav_path.write_bytes(_make_wav_bytes())

    try:
        resp = await client.get(f"/api/v1/audio/{filename}")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("audio/")
    finally:
        if wav_path.exists():
            wav_path.unlink()


async def test_serve_preview_success(client: AsyncClient, tmp_path: Path):
    """Create a real WAV file in the previews directory and verify it's served."""
    preview_dir = Path(settings.storage_path) / "output" / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)

    filename = "test_preview_fixture.wav"
    wav_path = preview_dir / filename
    wav_path.write_bytes(_make_wav_bytes())

    try:
        resp = await client.get(f"/api/v1/audio/previews/{filename}")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("audio/")
    finally:
        if wav_path.exists():
            wav_path.unlink()


# ---------------------------------------------------------------------------
# Directory traversal protection
# ---------------------------------------------------------------------------

async def test_directory_traversal_blocked(client: AsyncClient):
    """
    Path traversal sequences must be sanitized by Path(filename).name before
    the file lookup so they can never escape the output directory.
    The file won't exist regardless, so we expect a 404 — not a 200 serving
    an arbitrary file, and definitely not a 500.
    """
    traversal_payloads = [
        "../../../etc/passwd",
        "..%2F..%2F..%2Fetc%2Fpasswd",
        "....//....//etc/passwd",
        "%2e%2e%2fetc%2fpasswd",
    ]
    for payload in traversal_payloads:
        resp = await client.get(f"/api/v1/audio/{payload}")
        # Must not be 200 (would mean we served a real file outside output dir)
        assert resp.status_code != 200, (
            f"Traversal payload '{payload}' returned 200 — sanitization may be broken"
        )
        # Expected: 404 (file not found after sanitization), never a 500
        assert resp.status_code == 404, (
            f"Expected 404 for traversal payload '{payload}', got {resp.status_code}"
        )


async def test_directory_traversal_preview_blocked(client: AsyncClient):
    """Same traversal protection applies to the previews endpoint."""
    resp = await client.get("/api/v1/audio/previews/../../../etc/passwd")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Cache-Control headers
# ---------------------------------------------------------------------------

async def test_serve_audio_cache_headers(client: AsyncClient):
    """Audio responses include Cache-Control headers."""
    import struct
    from pathlib import Path

    from app.core.config import settings

    output_dir = Path(settings.storage_path) / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    test_file = output_dir / "cache_test.wav"

    # Write minimal WAV
    wav_data = b"RIFF" + struct.pack("<I", 36) + b"WAVEfmt "
    wav_data += struct.pack("<IHHIIHH", 16, 1, 1, 22050, 22050, 2, 16)
    wav_data += b"data" + struct.pack("<I", 0)
    test_file.write_bytes(wav_data)

    try:
        response = await client.get("/api/v1/audio/cache_test.wav")
        assert response.status_code == 200
        assert "Cache-Control" in response.headers
        assert "max-age=86400" in response.headers["Cache-Control"]
    finally:
        test_file.unlink(missing_ok=True)
