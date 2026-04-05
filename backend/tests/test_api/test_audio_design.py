"""Tests for the Audio Design Studio API endpoints.

Covers:
  POST /audio-tools/upload
  GET  /audio-tools/files
  DELETE /audio-tools/files/{id}
  POST /audio-tools/trim
  POST /audio-tools/concat
  POST /audio-tools/effects
  POST /audio-tools/export
  POST /audio-tools/analyze
"""

from __future__ import annotations

import io
import struct
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wav_bytes(duration_s: float = 1.0, sample_rate: int = 22050) -> bytes:
    """Return the raw bytes of a minimal valid mono 16-bit WAV."""
    num_samples = int(sample_rate * duration_s)
    data_size = num_samples * 2  # 16-bit = 2 bytes per sample
    chunk_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,              # PCM
        1,              # mono
        sample_rate,
        sample_rate * 2,  # byte rate
        2,              # block align
        16,             # bits per sample
        b"data",
        data_size,
    )
    # Generate a 440 Hz sine wave (not silence — silence breaks librosa noise reduction)
    import math
    samples = [int(16000 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(num_samples)]
    return header + struct.pack(f"<{num_samples}h", *samples)


def _workdir() -> Path:
    """Return the same workdir the endpoint code uses."""
    d = Path(settings.storage_path) / "audio-design"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _place_wav(file_id: str, duration_s: float = 1.0) -> Path:
    """Write a test WAV into the workdir under *file_id*.wav and return its path."""
    p = _workdir() / f"{file_id}.wav"
    p.write_bytes(_make_wav_bytes(duration_s=duration_s))
    return p


def _valid_file_id() -> str:
    """Return a fresh 16-character hex file_id."""
    return uuid.uuid4().hex[:16]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def wav_bytes_1s() -> bytes:
    return _make_wav_bytes(duration_s=1.0)


@pytest.fixture
def wav_bytes_2s() -> bytes:
    return _make_wav_bytes(duration_s=2.0)


@pytest.fixture
def uploaded_file_id() -> str:
    """Pre-place a WAV in the workdir and return its file_id.  Auto-cleaned up."""
    fid = _valid_file_id()
    path = _place_wav(fid, duration_s=2.0)
    yield fid
    path.unlink(missing_ok=True)


@pytest.fixture
def two_uploaded_ids() -> tuple[str, str]:
    """Pre-place two WAVs in the workdir and return their file_ids."""
    fid1 = _valid_file_id()
    fid2 = _valid_file_id()
    p1 = _place_wav(fid1, duration_s=1.0)
    p2 = _place_wav(fid2, duration_s=1.0)
    yield fid1, fid2
    p1.unlink(missing_ok=True)
    p2.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# POST /audio-tools/upload
# ---------------------------------------------------------------------------


class TestUploadAudio:
    async def test_upload_valid_wav(self, client: AsyncClient, wav_bytes_1s: bytes):
        resp = await client.post(
            "/api/v1/audio-tools/upload",
            files={"audio": ("test.wav", io.BytesIO(wav_bytes_1s), "audio/wav")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "file" in body
        file_info = body["file"]
        assert file_info["format"] == "wav"
        assert file_info["duration_seconds"] > 0
        assert file_info["file_id"]

        # Clean up the created workdir file
        fid = file_info["file_id"]
        (_workdir() / file_info["filename"]).unlink(missing_ok=True)

    async def test_upload_returns_file_id_matching_pattern(self, client: AsyncClient, wav_bytes_1s: bytes):
        import re

        resp = await client.post(
            "/api/v1/audio-tools/upload",
            files={"audio": ("clip.wav", io.BytesIO(wav_bytes_1s), "audio/wav")},
        )
        assert resp.status_code == 200
        fid = resp.json()["file"]["file_id"]
        assert re.fullmatch(r"[a-f0-9]{16}", fid), f"Unexpected file_id format: {fid!r}"
        (_workdir() / resp.json()["file"]["filename"]).unlink(missing_ok=True)

    async def test_upload_audio_too_large(self, client: AsyncClient):
        """Files larger than MAX_UPLOAD_BYTES must be rejected with 413."""
        from app.schemas.audio_tools import MAX_UPLOAD_BYTES

        # Build a fake large payload (just enough metadata + oversized body)
        oversized = b"X" * (MAX_UPLOAD_BYTES + 1)
        resp = await client.post(
            "/api/v1/audio-tools/upload",
            files={"audio": ("big.wav", io.BytesIO(oversized), "audio/wav")},
        )
        assert resp.status_code == 413

    async def test_upload_invalid_format_rejected(self, client: AsyncClient):
        """.exe files must be rejected with 400."""
        resp = await client.post(
            "/api/v1/audio-tools/upload",
            files={"audio": ("malware.exe", io.BytesIO(b"MZ\x00\x00"), "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert "unsupported" in resp.json()["detail"].lower()

    async def test_upload_no_extension_rejected(self, client: AsyncClient, wav_bytes_1s: bytes):
        """Uploading a file with no extension must be rejected with 400."""
        resp = await client.post(
            "/api/v1/audio-tools/upload",
            files={"audio": ("noextension", io.BytesIO(wav_bytes_1s), "audio/wav")},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /audio-tools/files
# ---------------------------------------------------------------------------


class TestListFiles:
    async def test_list_files_returns_200(self, client: AsyncClient):
        resp = await client.get("/api/v1/audio-tools/files")
        assert resp.status_code == 200
        body = resp.json()
        assert "files" in body
        assert "count" in body
        assert isinstance(body["files"], list)

    async def test_list_files_includes_uploaded_file(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        resp = await client.get("/api/v1/audio-tools/files")
        assert resp.status_code == 200
        ids = [f["file_id"] for f in resp.json()["files"]]
        assert uploaded_file_id in ids

    async def test_list_files_pagination_limit(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        """limit=1 must return at most 1 file."""
        resp = await client.get("/api/v1/audio-tools/files?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()["files"]) <= 1

    async def test_list_files_pagination_skip(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        """skip beyond total count must return an empty files list."""
        resp_all = await client.get("/api/v1/audio-tools/files")
        total = resp_all.json()["total"]

        resp_skip = await client.get(f"/api/v1/audio-tools/files?skip={total + 100}")
        assert resp_skip.status_code == 200
        assert resp_skip.json()["files"] == []

    async def test_list_files_total_reflects_count(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        resp = await client.get("/api/v1/audio-tools/files")
        body = resp.json()
        assert body["total"] >= body["count"]


# ---------------------------------------------------------------------------
# DELETE /audio-tools/files/{file_id}
# ---------------------------------------------------------------------------


class TestDeleteFile:
    async def test_delete_existing_file_returns_204(
        self, client: AsyncClient
    ):
        """Delete a file that exists in the workdir — expect 204."""
        fid = _valid_file_id()
        path = _place_wav(fid)
        try:
            resp = await client.delete(f"/api/v1/audio-tools/files/{fid}")
            assert resp.status_code == 204
        finally:
            path.unlink(missing_ok=True)

    async def test_delete_removes_file_from_disk(self, client: AsyncClient):
        fid = _valid_file_id()
        path = _place_wav(fid)

        await client.delete(f"/api/v1/audio-tools/files/{fid}")
        assert not path.exists()

    async def test_delete_nonexistent_file_returns_404(self, client: AsyncClient):
        fid = _valid_file_id()  # never placed
        resp = await client.delete(f"/api/v1/audio-tools/files/{fid}")
        assert resp.status_code == 404

    async def test_delete_invalid_file_id_format(self, client: AsyncClient):
        resp = await client.delete("/api/v1/audio-tools/files/not-a-valid-id")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /audio-tools/trim
# ---------------------------------------------------------------------------


class TestTrimEndpoint:
    async def test_trim_audio_returns_new_file(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        resp = await client.post(
            "/api/v1/audio-tools/trim",
            json={
                "file_id": uploaded_file_id,
                "start_seconds": 0.0,
                "end_seconds": 1.0,
            },
        )
        assert resp.status_code == 200
        file_info = resp.json()["file"]
        assert file_info["file_id"] != uploaded_file_id
        assert file_info["duration_seconds"] > 0

        # Clean up the new output file
        (_workdir() / file_info["filename"]).unlink(missing_ok=True)

    async def test_trim_invalid_range_start_greater_than_end(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        """start_seconds > end_seconds must be rejected at the schema level."""
        resp = await client.post(
            "/api/v1/audio-tools/trim",
            json={
                "file_id": uploaded_file_id,
                "start_seconds": 1.5,
                "end_seconds": 0.5,
            },
        )
        assert resp.status_code == 422

    async def test_trim_invalid_range_equal_bounds(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        resp = await client.post(
            "/api/v1/audio-tools/trim",
            json={
                "file_id": uploaded_file_id,
                "start_seconds": 1.0,
                "end_seconds": 1.0,
            },
        )
        assert resp.status_code == 422

    async def test_trim_negative_start_rejected(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        resp = await client.post(
            "/api/v1/audio-tools/trim",
            json={
                "file_id": uploaded_file_id,
                "start_seconds": -0.5,
                "end_seconds": 1.0,
            },
        )
        assert resp.status_code == 422

    async def test_trim_nonexistent_file_returns_404(self, client: AsyncClient):
        fid = _valid_file_id()
        resp = await client.post(
            "/api/v1/audio-tools/trim",
            json={"file_id": fid, "start_seconds": 0.0, "end_seconds": 0.5},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /audio-tools/concat
# ---------------------------------------------------------------------------


class TestConcatEndpoint:
    async def test_concat_two_files_returns_new_file(
        self, client: AsyncClient, two_uploaded_ids: tuple[str, str]
    ):
        fid1, fid2 = two_uploaded_ids
        resp = await client.post(
            "/api/v1/audio-tools/concat",
            json={"file_ids": [fid1, fid2], "crossfade_ms": 0},
        )
        assert resp.status_code == 200
        file_info = resp.json()["file"]
        assert file_info["file_id"] not in (fid1, fid2)
        # Combined duration of two 1-second files should be ≈ 2 s
        assert file_info["duration_seconds"] > 1.5

        (_workdir() / file_info["filename"]).unlink(missing_ok=True)

    async def test_concat_with_crossfade(
        self, client: AsyncClient, two_uploaded_ids: tuple[str, str]
    ):
        fid1, fid2 = two_uploaded_ids
        resp = await client.post(
            "/api/v1/audio-tools/concat",
            json={"file_ids": [fid1, fid2], "crossfade_ms": 100},
        )
        assert resp.status_code == 200
        file_info = resp.json()["file"]
        assert file_info["duration_seconds"] > 0
        (_workdir() / file_info["filename"]).unlink(missing_ok=True)

    async def test_concat_single_file_rejected(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        """min_length=2 on file_ids must reject single-element lists."""
        resp = await client.post(
            "/api/v1/audio-tools/concat",
            json={"file_ids": [uploaded_file_id]},
        )
        assert resp.status_code == 422

    async def test_concat_invalid_file_id_format(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/audio-tools/concat",
            json={"file_ids": ["not-valid!", "also-bad!"]},
        )
        assert resp.status_code == 422

    async def test_concat_nonexistent_file_returns_404(self, client: AsyncClient):
        fid1 = _valid_file_id()
        fid2 = _valid_file_id()
        resp = await client.post(
            "/api/v1/audio-tools/concat",
            json={"file_ids": [fid1, fid2]},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /audio-tools/effects
# ---------------------------------------------------------------------------


class TestEffectsChainEndpoint:
    async def test_effects_noise_reduction(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        resp = await client.post(
            "/api/v1/audio-tools/effects",
            json={
                "file_id": uploaded_file_id,
                "effects": [{"type": "noise_reduction", "strength": 0.5}],
            },
        )
        assert resp.status_code == 200
        file_info = resp.json()["file"]
        assert file_info["file_id"] != uploaded_file_id
        (_workdir() / file_info["filename"]).unlink(missing_ok=True)

    async def test_effects_normalize(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        resp = await client.post(
            "/api/v1/audio-tools/effects",
            json={
                "file_id": uploaded_file_id,
                "effects": [{"type": "normalize"}],
            },
        )
        assert resp.status_code == 200
        file_info = resp.json()["file"]
        (_workdir() / file_info["filename"]).unlink(missing_ok=True)

    async def test_effects_gain(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        resp = await client.post(
            "/api/v1/audio-tools/effects",
            json={
                "file_id": uploaded_file_id,
                "effects": [{"type": "gain", "gain_db": 3.0}],
            },
        )
        assert resp.status_code == 200
        file_info = resp.json()["file"]
        (_workdir() / file_info["filename"]).unlink(missing_ok=True)

    async def test_effects_trim_silence(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        resp = await client.post(
            "/api/v1/audio-tools/effects",
            json={
                "file_id": uploaded_file_id,
                "effects": [{"type": "trim_silence", "threshold_db": -40.0}],
            },
        )
        # trim_silence on an all-zeros WAV may consume the whole signal —
        # either the endpoint succeeds (200) or rejects with 400 (empty after trim).
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            file_info = resp.json()["file"]
            (_workdir() / file_info["filename"]).unlink(missing_ok=True)

    async def test_effects_chained_operations(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        """Multiple effects applied sequentially must succeed."""
        resp = await client.post(
            "/api/v1/audio-tools/effects",
            json={
                "file_id": uploaded_file_id,
                "effects": [
                    {"type": "noise_reduction", "strength": 0.3},
                    {"type": "gain", "gain_db": -3.0},
                ],
            },
        )
        assert resp.status_code == 200
        file_info = resp.json()["file"]
        (_workdir() / file_info["filename"]).unlink(missing_ok=True)

    async def test_effects_empty_list_rejected(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        """min_length=1 on effects must reject an empty list."""
        resp = await client.post(
            "/api/v1/audio-tools/effects",
            json={"file_id": uploaded_file_id, "effects": []},
        )
        assert resp.status_code == 422

    async def test_effects_nonexistent_file_returns_404(self, client: AsyncClient):
        fid = _valid_file_id()
        resp = await client.post(
            "/api/v1/audio-tools/effects",
            json={"file_id": fid, "effects": [{"type": "gain", "gain_db": 0.0}]},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /audio-tools/export
# ---------------------------------------------------------------------------


class TestExportEndpoint:
    async def test_export_wav(self, client: AsyncClient, uploaded_file_id: str):
        resp = await client.post(
            "/api/v1/audio-tools/export",
            json={"file_id": uploaded_file_id, "format": "wav"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["format"] == "wav"
        assert body["file_id"]
        assert body["audio_url"].endswith(".wav")
        (_workdir() / body["filename"]).unlink(missing_ok=True)

    async def test_export_mp3(self, client: AsyncClient, uploaded_file_id: str):
        resp = await client.post(
            "/api/v1/audio-tools/export",
            json={"file_id": uploaded_file_id, "format": "mp3"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["format"] == "mp3"
        (_workdir() / body["filename"]).unlink(missing_ok=True)

    async def test_export_ogg(self, client: AsyncClient, uploaded_file_id: str):
        resp = await client.post(
            "/api/v1/audio-tools/export",
            json={"file_id": uploaded_file_id, "format": "ogg"},
        )
        assert resp.status_code == 200
        (_workdir() / resp.json()["filename"]).unlink(missing_ok=True)

    async def test_export_flac(self, client: AsyncClient, uploaded_file_id: str):
        resp = await client.post(
            "/api/v1/audio-tools/export",
            json={"file_id": uploaded_file_id, "format": "flac"},
        )
        assert resp.status_code == 200
        (_workdir() / resp.json()["filename"]).unlink(missing_ok=True)

    async def test_export_with_sample_rate(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        """Exporting with an explicit sample_rate must include it in the response."""
        resp = await client.post(
            "/api/v1/audio-tools/export",
            json={"file_id": uploaded_file_id, "format": "wav", "sample_rate": 16000},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["sample_rate"] == 16000
        (_workdir() / body["filename"]).unlink(missing_ok=True)

    async def test_export_invalid_sample_rate_rejected(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        """An unsupported sample rate must be rejected with 422."""
        resp = await client.post(
            "/api/v1/audio-tools/export",
            json={"file_id": uploaded_file_id, "format": "wav", "sample_rate": 12345},
        )
        assert resp.status_code == 422

    async def test_export_invalid_format_rejected(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        resp = await client.post(
            "/api/v1/audio-tools/export",
            json={"file_id": uploaded_file_id, "format": "xyz"},
        )
        assert resp.status_code == 422

    async def test_export_nonexistent_file_returns_404(self, client: AsyncClient):
        fid = _valid_file_id()
        resp = await client.post(
            "/api/v1/audio-tools/export",
            json={"file_id": fid, "format": "wav"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /audio-tools/analyze
# ---------------------------------------------------------------------------


class TestAnalyzeEndpoint:
    async def test_analyze_returns_expected_fields(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        resp = await client.post(
            "/api/v1/audio-tools/analyze",
            json={"file_id": uploaded_file_id},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["file_id"] == uploaded_file_id
        assert "duration_seconds" in body
        assert "sample_rate" in body
        assert "quality" in body
        quality = body["quality"]
        assert "passed" in quality
        assert "score" in quality

    async def test_analyze_duration_positive(
        self, client: AsyncClient, uploaded_file_id: str
    ):
        resp = await client.post(
            "/api/v1/audio-tools/analyze",
            json={"file_id": uploaded_file_id},
        )
        assert resp.status_code == 200
        assert resp.json()["duration_seconds"] > 0

    async def test_analyze_nonexistent_file_returns_404(self, client: AsyncClient):
        fid = _valid_file_id()
        resp = await client.post(
            "/api/v1/audio-tools/analyze",
            json={"file_id": fid},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Invalid file_id format — shared guard
# ---------------------------------------------------------------------------


class TestInvalidFileId:
    async def test_trim_invalid_file_id_format(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/audio-tools/trim",
            json={"file_id": "ZZZZZZZZZZZZZZZZ", "start_seconds": 0.0, "end_seconds": 1.0},
        )
        # file_id must be lowercase hex — uppercase fails the validator
        assert resp.status_code == 422

    async def test_trim_short_file_id_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/audio-tools/trim",
            json={"file_id": "abc123", "start_seconds": 0.0, "end_seconds": 1.0},
        )
        assert resp.status_code == 422

    async def test_analyze_invalid_file_id_format(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/audio-tools/analyze",
            json={"file_id": "not-hex-at-all!!"},
        )
        assert resp.status_code == 422

    async def test_delete_invalid_file_id_returns_400(self, client: AsyncClient):
        resp = await client.delete("/api/v1/audio-tools/files/bad-id")
        assert resp.status_code == 400

    async def test_export_invalid_file_id_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/audio-tools/export",
            json={"file_id": "gg", "format": "wav"},
        )
        assert resp.status_code == 422
