"""Endpoint tests for /audio-tools/enhance (AP-43) and /audiobook/render (AP-41).

These tests mock the heavy audio_enhancement / audiobook_stitcher service
calls so we exercise the endpoint glue without ffmpeg/loudness dependencies.
"""

from __future__ import annotations

import struct
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.schemas.profile import ProfileCreate
from app.services.audiobook_stitcher import AudiobookResult, ChapterMarker
from app.services.profile_service import create_profile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav_bytes() -> bytes:
    import math

    sr, duration_s = 16000, 1.0
    n = int(sr * duration_s)
    data = n * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data, b"WAVE",
        b"fmt ", 16, 1, 1, sr, sr * 2, 2, 16,
        b"data", data,
    )
    samples = [int(8000 * math.sin(2 * math.pi * 220 * i / sr)) for i in range(n)]
    return header + struct.pack(f"<{n}h", *samples)


def _workdir() -> Path:
    d = Path(settings.storage_path) / "audio-design"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def placed_wav_id() -> str:
    fid = uuid.uuid4().hex[:16]
    path = _workdir() / f"{fid}.wav"
    path.write_bytes(_make_wav_bytes())
    yield fid
    path.unlink(missing_ok=True)


@pytest.fixture
def placed_music_id() -> str:
    fid = uuid.uuid4().hex[:16]
    path = _workdir() / f"{fid}.wav"
    path.write_bytes(_make_wav_bytes())
    yield fid
    path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# /audio-tools/enhance
# ---------------------------------------------------------------------------

class TestEnhanceEndpoint:
    @pytest.mark.asyncio
    async def test_denoise_mode_returns_200(self, client: AsyncClient, placed_wav_id: str):
        out_path = Path(settings.storage_path) / "output" / "denoised_test.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(_make_wav_bytes())

        with patch(
            "app.services.audio_enhancement.denoise",
            AsyncMock(return_value=out_path),
        ):
            resp = await client.post(
                "/api/v1/audio-tools/enhance",
                json={"file_id": placed_wav_id, "mode": "denoise"},
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mode"] == "denoise"
        assert body["output_filename"] == out_path.name
        assert body["audio_url"].endswith(out_path.name)

    @pytest.mark.asyncio
    async def test_dereverb_mode_returns_200(self, client: AsyncClient, placed_wav_id: str):
        out_path = Path(settings.storage_path) / "output" / "drv_test.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(_make_wav_bytes())

        with patch(
            "app.services.audio_enhancement.dereverb",
            AsyncMock(return_value=out_path),
        ):
            resp = await client.post(
                "/api/v1/audio-tools/enhance",
                json={"file_id": placed_wav_id, "mode": "dereverb"},
            )
        assert resp.status_code == 200
        assert resp.json()["mode"] == "dereverb"

    @pytest.mark.asyncio
    async def test_duck_mode_requires_music_id(self, client: AsyncClient, placed_wav_id: str):
        resp = await client.post(
            "/api/v1/audio-tools/enhance",
            json={"file_id": placed_wav_id, "mode": "duck"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_duck_mode_returns_200(
        self, client: AsyncClient, placed_wav_id: str, placed_music_id: str
    ):
        out_path = Path(settings.storage_path) / "output" / "duck_test.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(_make_wav_bytes())

        with patch(
            "app.services.audio_enhancement.duck_music",
            AsyncMock(return_value=out_path),
        ):
            resp = await client.post(
                "/api/v1/audio-tools/enhance",
                json={
                    "file_id": placed_wav_id,
                    "music_file_id": placed_music_id,
                    "mode": "duck",
                    "speech_duck_db": -15,
                },
            )
        assert resp.status_code == 200
        assert resp.json()["mode"] == "duck"

    @pytest.mark.asyncio
    async def test_unknown_mode_rejected(self, client: AsyncClient, placed_wav_id: str):
        resp = await client.post(
            "/api/v1/audio-tools/enhance",
            json={"file_id": placed_wav_id, "mode": "nope"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /audiobook/render
# ---------------------------------------------------------------------------

class TestAudiobookEndpoint:
    @pytest.mark.asyncio
    async def test_render_returns_markers_and_url(self, client: AsyncClient, db_session):
        profile = await create_profile(
            db_session,
            ProfileCreate(name="Book", provider_name="kokoro", voice_id="af_heart"),
        )
        await db_session.commit()

        out_path = Path(settings.storage_path) / "output" / f"audiobook_{uuid.uuid4().hex[:12]}.mp3"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"ID3 stub")

        fake_result = AudiobookResult(
            output_path=out_path,
            duration_seconds=12.5,
            chapter_markers=[
                ChapterMarker(index=0, title="Chapter 1", start_seconds=0.0, end_seconds=6.0),
                ChapterMarker(index=1, title="Chapter 2", start_seconds=6.0, end_seconds=12.5),
            ],
            paragraph_count=3,
            loudness_lufs=-16.1,
            loudness_fallback=False,
        )

        with patch(
            "app.api.v1.endpoints.audiobook.render_audiobook",
            AsyncMock(return_value=fake_result),
        ):
            resp = await client.post(
                "/api/v1/audiobook/render",
                json={
                    "profile_id": profile.id,
                    "markdown": "# Ch1\n\npara\n\n# Ch2\n\npara",
                    "target_lufs": -16.0,
                    "crossfade_ms": 300,
                },
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["paragraph_count"] == 3
        assert body["duration_seconds"] == 12.5
        assert body["output_filename"] == out_path.name
        assert body["audio_url"].endswith(out_path.name)
        assert len(body["chapter_markers"]) == 2
        assert body["chapter_markers"][0]["title"] == "Chapter 1"
        assert body["loudness_lufs"] == -16.1
        out_path.unlink(missing_ok=True)
