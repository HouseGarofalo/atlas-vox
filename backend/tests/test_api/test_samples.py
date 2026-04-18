"""Tests for audio sample upload/list/delete/analysis endpoints."""

from __future__ import annotations

import io
import struct
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav_bytes() -> bytes:
    """Build a minimal valid WAV file in memory (mono, 22050 Hz, 1 sec)."""
    sample_rate = 22050
    num_channels = 1
    bits_per_sample = 16
    num_samples = sample_rate
    data_size = num_samples * num_channels * (bits_per_sample // 8)
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        sample_rate * num_channels * (bits_per_sample // 8),
        num_channels * (bits_per_sample // 8),
        bits_per_sample,
        b"data",
        data_size,
    )
    samples = struct.pack(f"<{num_samples}h", *([0] * num_samples))
    return header + samples


async def _create_profile(client: AsyncClient, name: str = "Sample Profile") -> str:
    resp = await client.post("/api/v1/profiles", json={
        "name": name,
        "provider_name": "kokoro",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

async def test_upload_sample_success(client: AsyncClient, tmp_path: Path):
    profile_id = await _create_profile(client)
    wav_data = _make_wav_bytes()

    from app.services.audio_processor import AudioAnalysis

    mock_analysis = AudioAnalysis(
        duration_seconds=1.0,
        sample_rate=22050,
        pitch_mean=150.0,
        pitch_std=10.0,
        energy_mean=0.05,
        energy_std=0.01,
    )

    with patch("app.api.v1.endpoints.samples.analyze_audio", new=AsyncMock(return_value=mock_analysis)):
        resp = await client.post(
            f"/api/v1/profiles/{profile_id}/samples",
            files={"files": ("voice_sample.wav", io.BytesIO(wav_data), "audio/wav")},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    sample = data[0]
    assert sample["profile_id"] == profile_id
    assert sample["format"] == "wav"
    assert sample["original_filename"] == "voice_sample.wav"


async def test_upload_sample_invalid_format(client: AsyncClient):
    profile_id = await _create_profile(client)
    resp = await client.post(
        f"/api/v1/profiles/{profile_id}/samples",
        files={"files": ("malware.exe", io.BytesIO(b"\x00\x01\x02"), "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "exe" in resp.json()["detail"].lower() or "unsupported" in resp.json()["detail"].lower()


async def test_upload_sample_no_profile(client: AsyncClient):
    wav_data = _make_wav_bytes()
    resp = await client.post(
        "/api/v1/profiles/nonexistent-profile/samples",
        files={"files": ("voice.wav", io.BytesIO(wav_data), "audio/wav")},
    )
    assert resp.status_code == 404


async def test_upload_too_many_files(client: AsyncClient):
    """Uploading more than MAX_FILES_PER_UPLOAD files should return 400."""
    profile_id = await _create_profile(client)
    wav_data = _make_wav_bytes()

    # MAX_FILES_PER_UPLOAD is 20; send 21
    files = [
        ("files", (f"voice_{i}.wav", io.BytesIO(wav_data), "audio/wav"))
        for i in range(21)
    ]
    resp = await client.post(
        f"/api/v1/profiles/{profile_id}/samples",
        files=files,
    )
    assert resp.status_code == 400
    assert "maximum" in resp.json()["detail"].lower() or "20" in resp.json()["detail"]


async def test_upload_aggregate_size_cap(client: AsyncClient, monkeypatch):
    """P1-13: Uploads whose aggregate size exceeds MAX_TOTAL_UPLOAD_BYTES must 413."""
    import app.api.v1.endpoints.samples as samples_mod

    # Shrink caps for a fast test: 30KB per file, 50KB aggregate.
    monkeypatch.setattr(samples_mod, "MAX_FILE_SIZE", 30 * 1024)
    monkeypatch.setattr(samples_mod, "MAX_TOTAL_UPLOAD_BYTES", 50 * 1024)

    profile_id = await _create_profile(client)
    # 3 × 25KB wav blobs = 75KB > 50KB aggregate cap but each < 30KB per-file.
    blob = b"RIFF" + (b"\x00" * (25 * 1024 - 4))
    files = [
        ("files", (f"v{i}.wav", io.BytesIO(blob), "audio/wav"))
        for i in range(3)
    ]
    resp = await client.post(
        f"/api/v1/profiles/{profile_id}/samples",
        files=files,
    )
    assert resp.status_code == 413
    assert "aggregate" in resp.json()["detail"].lower() or "50" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

async def test_list_samples_empty(client: AsyncClient):
    profile_id = await _create_profile(client, name="Empty Profile")
    resp = await client.get(f"/api/v1/profiles/{profile_id}/samples")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["samples"] == []


async def test_list_samples(client: AsyncClient, tmp_path: Path):
    profile_id = await _create_profile(client)

    from app.services.audio_processor import AudioAnalysis

    mock_analysis = AudioAnalysis(
        duration_seconds=1.0,
        sample_rate=22050,
        pitch_mean=150.0,
        pitch_std=10.0,
        energy_mean=0.05,
        energy_std=0.01,
    )

    # Upload a sample via HTTP to populate the table
    with patch("app.api.v1.endpoints.samples.analyze_audio", new=AsyncMock(return_value=mock_analysis)):
        upload_resp = await client.post(
            f"/api/v1/profiles/{profile_id}/samples",
            files={"files": ("voice.wav", io.BytesIO(_make_wav_bytes()), "audio/wav")},
        )
    assert upload_resp.status_code == 201

    resp = await client.get(f"/api/v1/profiles/{profile_id}/samples")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert any(s["original_filename"] == "voice.wav" for s in data["samples"])


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

async def test_delete_sample(client: AsyncClient, tmp_path: Path):
    profile_id = await _create_profile(client)

    from app.services.audio_processor import AudioAnalysis

    mock_analysis = AudioAnalysis(
        duration_seconds=1.0,
        sample_rate=22050,
        pitch_mean=150.0,
        pitch_std=10.0,
        energy_mean=0.05,
        energy_std=0.01,
    )

    with patch("app.api.v1.endpoints.samples.analyze_audio", new=AsyncMock(return_value=mock_analysis)):
        upload_resp = await client.post(
            f"/api/v1/profiles/{profile_id}/samples",
            files={"files": ("del_voice.wav", io.BytesIO(_make_wav_bytes()), "audio/wav")},
        )
    assert upload_resp.status_code == 201
    sample_id = upload_resp.json()[0]["id"]

    resp = await client.delete(f"/api/v1/profiles/{profile_id}/samples/{sample_id}")
    assert resp.status_code == 204

    # Confirm it's gone
    get_resp = await client.get(f"/api/v1/profiles/{profile_id}/samples")
    assert all(s["id"] != sample_id for s in get_resp.json()["samples"])


async def test_delete_sample_not_found(client: AsyncClient):
    profile_id = await _create_profile(client)
    resp = await client.delete(f"/api/v1/profiles/{profile_id}/samples/no-such-sample-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

async def test_sample_analysis(client: AsyncClient, tmp_path: Path):
    profile_id = await _create_profile(client)

    from app.services.audio_processor import AudioAnalysis

    mock_analysis = AudioAnalysis(
        duration_seconds=2.5,
        sample_rate=44100,
        pitch_mean=180.0,
        pitch_std=12.0,
        energy_mean=0.07,
        energy_std=0.02,
    )

    with patch("app.api.v1.endpoints.samples.analyze_audio", new=AsyncMock(return_value=mock_analysis)):
        upload_resp = await client.post(
            f"/api/v1/profiles/{profile_id}/samples",
            files={"files": ("analysis.wav", io.BytesIO(_make_wav_bytes()), "audio/wav")},
        )
    assert upload_resp.status_code == 201
    sample_id = upload_resp.json()[0]["id"]

    # Analysis is cached during upload; retrieve it via the analysis endpoint
    resp = await client.get(f"/api/v1/profiles/{profile_id}/samples/{sample_id}/analysis")
    assert resp.status_code == 200
    result = resp.json()
    assert result["sample_id"] == sample_id
    assert result["duration_seconds"] == pytest.approx(2.5, abs=0.1)
    assert result["sample_rate"] == 44100


# ---------------------------------------------------------------------------
# Preprocessing trigger
# ---------------------------------------------------------------------------

async def test_trigger_preprocessing_no_samples(client: AsyncClient):
    """With no unprocessed samples the endpoint returns a 202 with no task_id."""
    profile_id = await _create_profile(client)

    resp = await client.post(f"/api/v1/profiles/{profile_id}/samples/preprocess")
    assert resp.status_code == 202
    data = resp.json()
    assert data["task_id"] is None
    assert "preprocessed" in data["message"].lower()


async def test_trigger_preprocessing(client: AsyncClient, tmp_path: Path):
    profile_id = await _create_profile(client)

    from app.services.audio_processor import AudioAnalysis

    mock_analysis = AudioAnalysis(
        duration_seconds=1.0,
        sample_rate=22050,
        pitch_mean=150.0,
        pitch_std=10.0,
        energy_mean=0.05,
        energy_std=0.01,
    )

    # Upload a sample so there's something unprocessed to preprocess
    with patch("app.api.v1.endpoints.samples.analyze_audio", new=AsyncMock(return_value=mock_analysis)):
        upload_resp = await client.post(
            f"/api/v1/profiles/{profile_id}/samples",
            files={"files": ("preprocess.wav", io.BytesIO(_make_wav_bytes()), "audio/wav")},
        )
    assert upload_resp.status_code == 201

    mock_task = MagicMock()
    mock_task.id = "celery-task-abc123"

    # preprocess_samples is imported inline inside the endpoint handler;
    # patch the Celery task at its source module
    with patch("app.tasks.preprocessing.preprocess_samples") as mock_preprocess:
        mock_preprocess.delay = MagicMock(return_value=mock_task)
        resp = await client.post(f"/api/v1/profiles/{profile_id}/samples/preprocess")

    assert resp.status_code == 202
    data = resp.json()
    assert data["task_id"] == "celery-task-abc123"
