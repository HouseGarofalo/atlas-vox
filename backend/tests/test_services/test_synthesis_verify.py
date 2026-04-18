"""Tests for SL-28 — synthesize dispatches verify_synthesis and history
endpoints surface the quality_flagged field."""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.synthesis import (
    QUALITY_WER_FLAG_THRESHOLD,
    _is_quality_flagged,
)
from app.models.synthesis_history import SynthesisHistory
from app.providers.base import AudioResult
from app.schemas.profile import ProfileCreate
from app.services.profile_service import create_profile
from app.services.synthesis_service import synthesize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wav_bytes(num_samples: int = 22050, sample_rate: int = 22050) -> bytes:
    num_channels, bits = 1, 16
    data_size = num_samples * num_channels * (bits // 8)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, num_channels, sample_rate,
        sample_rate * num_channels * (bits // 8),
        num_channels * (bits // 8), bits,
        b"data", data_size,
    )
    return header + struct.pack(f"<{num_samples}h", *([0] * num_samples))


def _temp_wav() -> Path:
    tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tf.write(_wav_bytes())
    tf.flush()
    tf.close()
    return Path(tf.name)


async def _make_profile(db: AsyncSession, name: str = "Verify Synth"):
    return await create_profile(
        db, ProfileCreate(name=name, provider_name="kokoro", voice_id="af_heart")
    )


def _mock_provider(wav: Path) -> AsyncMock:
    audio = AudioResult(audio_path=wav, duration_seconds=1.0, sample_rate=22050, format="wav")
    provider = AsyncMock()
    provider.synthesize = AsyncMock(return_value=audio)
    provider.get_capabilities = AsyncMock(return_value=MagicMock(
        supports_word_boundaries=False, supports_streaming=False,
    ))
    return provider


# ---------------------------------------------------------------------------
# synthesize dispatches verify_synthesis task (fire-and-forget)
# ---------------------------------------------------------------------------

async def test_synthesize_dispatches_verify_task(db_session: AsyncSession):
    profile = await _make_profile(db_session)
    wav = _temp_wav()
    provider = _mock_provider(wav)

    with patch(
        "app.services.synthesis_service.provider_registry.get_provider",
        return_value=provider,
    ), patch(
        "app.tasks.preferences.verify_synthesis.delay",
    ) as mock_delay:
        result = await synthesize(
            db_session, text="hello world.", profile_id=profile.id,
        )

    # Exactly one dispatch per synthesis, with the new history id.
    assert mock_delay.called
    called_args = mock_delay.call_args.args
    assert called_args[0] == result["id"]


async def test_synthesize_swallows_dispatch_errors(db_session: AsyncSession):
    """If the broker is unreachable, synthesize must still succeed."""
    profile = await _make_profile(db_session)
    wav = _temp_wav()
    provider = _mock_provider(wav)

    with patch(
        "app.services.synthesis_service.provider_registry.get_provider",
        return_value=provider,
    ), patch(
        "app.tasks.preferences.verify_synthesis.delay",
        side_effect=RuntimeError("broker down"),
    ):
        result = await synthesize(
            db_session, text="hi", profile_id=profile.id,
        )

    # Synthesis still returned a valid dict even though dispatch failed.
    assert result["id"]
    assert result["audio_url"].startswith("/api/v1/audio/")


# ---------------------------------------------------------------------------
# quality_flagged computation on the history endpoint
# ---------------------------------------------------------------------------

def test_quality_flagged_below_threshold_is_false():
    assert _is_quality_flagged(0.0) is False
    assert _is_quality_flagged(QUALITY_WER_FLAG_THRESHOLD) is False


def test_quality_flagged_above_threshold_is_true():
    assert _is_quality_flagged(QUALITY_WER_FLAG_THRESHOLD + 0.01) is True
    assert _is_quality_flagged(0.99) is True


def test_quality_flagged_null_is_false():
    assert _is_quality_flagged(None) is False


async def test_history_endpoint_surfaces_quality_flags(
    client: AsyncClient, db_session: AsyncSession
):
    """The /synthesis/history endpoint must include quality_flagged per row."""
    profile = await _make_profile(db_session, name="History Flag Test")

    good = SynthesisHistory(
        profile_id=profile.id, provider_name="kokoro",
        text="good", output_path="/tmp/g.wav",
        output_format="wav", duration_seconds=1.0, latency_ms=10,
        quality_wer=0.05,
    )
    bad = SynthesisHistory(
        profile_id=profile.id, provider_name="kokoro",
        text="bad", output_path="/tmp/b.wav",
        output_format="wav", duration_seconds=1.0, latency_ms=10,
        quality_wer=0.9,
    )
    pending = SynthesisHistory(
        profile_id=profile.id, provider_name="kokoro",
        text="pending", output_path="/tmp/p.wav",
        output_format="wav", duration_seconds=1.0, latency_ms=10,
        quality_wer=None,
    )
    db_session.add_all([good, bad, pending])
    await db_session.flush()

    resp = await client.get(f"/api/v1/synthesis/history?profile_id={profile.id}")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    by_text = {r["text"]: r for r in rows}

    assert by_text["good"]["quality_flagged"] is False
    assert by_text["good"]["quality_wer"] == pytest.approx(0.05)
    assert by_text["bad"]["quality_flagged"] is True
    assert by_text["bad"]["quality_wer"] == pytest.approx(0.9)
    assert by_text["pending"]["quality_flagged"] is False
    assert by_text["pending"]["quality_wer"] is None
