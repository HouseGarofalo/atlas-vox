"""Tests for synthesis service — text chunking, synthesize, batch, history."""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persona_preset import PersonaPreset
from app.models.synthesis_history import SynthesisHistory
from app.providers.base import AudioResult
from app.schemas.profile import ProfileCreate
from app.services.profile_service import create_profile
from app.services.synthesis_service import (
    _split_text,
    batch_synthesize,
    get_history,
    synthesize,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav_bytes(num_samples: int = 22050, sample_rate: int = 22050) -> bytes:
    """Return a minimal valid WAV file as bytes."""
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


def _make_temp_wav() -> Path:
    """Write a real WAV file to a temp location and return its Path."""
    tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tf.write(_make_wav_bytes())
    tf.flush()
    tf.close()
    return Path(tf.name)


async def _make_profile(db: AsyncSession, name: str = "Test Profile", provider: str = "kokoro"):
    return await create_profile(db, ProfileCreate(name=name, provider_name=provider, voice_id="af_heart"))


def _mock_provider(wav_path: Path) -> AsyncMock:
    """Build a mock provider whose synthesize() returns a real AudioResult."""
    audio_result = AudioResult(
        audio_path=wav_path,
        duration_seconds=1.0,
        sample_rate=22050,
        format="wav",
    )
    provider = AsyncMock()
    provider.synthesize = AsyncMock(return_value=audio_result)
    return provider


# ---------------------------------------------------------------------------
# _split_text (existing suite preserved)
# ---------------------------------------------------------------------------

class TestTextChunking:
    def test_short_text_no_split(self):
        chunks = _split_text("Hello world.", max_chars=1000)
        assert chunks == ["Hello world."]

    def test_splits_at_sentence_boundary(self):
        text = "First sentence. Second sentence. Third sentence."
        chunks = _split_text(text, max_chars=30)
        assert len(chunks) >= 2
        rejoined = " ".join(chunks)
        assert "First sentence." in rejoined
        assert "Third sentence." in rejoined

    def test_handles_long_sentence(self):
        text = "word " * 500
        chunks = _split_text(text.strip(), max_chars=100)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 100

    def test_empty_text(self):
        chunks = _split_text("", max_chars=1000)
        assert chunks == [""]

    def test_exact_boundary(self):
        text = "A" * 1000
        chunks = _split_text(text, max_chars=1000)
        assert chunks == [text]


# ---------------------------------------------------------------------------
# synthesize
# ---------------------------------------------------------------------------

async def test_synthesize_success(db_session: AsyncSession):
    """Happy-path: synthesize returns dict with all expected keys."""
    profile = await _make_profile(db_session)
    wav_path = _make_temp_wav()

    mock_provider = _mock_provider(wav_path)
    with patch(
        "app.services.synthesis_service.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        result = await synthesize(db_session, text="Hello world.", profile_id=profile.id)

    assert "id" in result
    assert "audio_url" in result
    assert "duration_seconds" in result
    assert "latency_ms" in result
    assert result["profile_id"] == profile.id
    assert result["provider_name"] == profile.provider_name
    assert result["audio_url"].startswith("/api/v1/audio/")


async def test_synthesize_with_preset(db_session: AsyncSession):
    """When preset_id is supplied, preset values must override defaults."""
    profile = await _make_profile(db_session)

    preset = PersonaPreset(name="Fast Narrator", speed=1.8, pitch=5.0, volume=0.9)
    db_session.add(preset)
    await db_session.flush()

    wav_path = _make_temp_wav()
    mock_provider = _mock_provider(wav_path)

    with patch(
        "app.services.synthesis_service.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        result = await synthesize(
            db_session,
            text="Narrator speaks.",
            profile_id=profile.id,
            preset_id=preset.id,
        )

    # Preset was applied — call must have completed without error
    assert result["profile_id"] == profile.id
    # Verify synthesize was invoked with the right settings by inspecting the
    # captured SynthesisSettings argument speed value
    call_args = mock_provider.synthesize.call_args
    synth_settings = call_args[0][2]  # positional arg index 2
    assert synth_settings.speed == pytest.approx(1.8)
    assert synth_settings.pitch == pytest.approx(5.0)
    assert synth_settings.volume == pytest.approx(0.9)


async def test_synthesize_invalid_profile(db_session: AsyncSession):
    """Nonexistent profile_id must raise ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await synthesize(db_session, text="Hello.", profile_id="no-such-profile-id")


async def test_synthesize_records_history(db_session: AsyncSession):
    """After synthesize(), a SynthesisHistory row must be persisted."""
    from sqlalchemy import select

    profile = await _make_profile(db_session)
    wav_path = _make_temp_wav()
    mock_provider = _mock_provider(wav_path)

    with patch(
        "app.services.synthesis_service.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        result = await synthesize(db_session, text="Record this.", profile_id=profile.id)

    rows = await db_session.execute(
        select(SynthesisHistory).where(SynthesisHistory.profile_id == profile.id)
    )
    history_list = list(rows.scalars().all())
    assert len(history_list) >= 1
    record = history_list[0]
    assert record.id == result["id"]
    assert record.provider_name == profile.provider_name
    assert "Record this." in record.text


async def test_batch_synthesize(db_session: AsyncSession):
    """batch_synthesize with 3 non-empty lines must return 3 results."""
    profile = await _make_profile(db_session)

    def _fresh_result():
        return AudioResult(
            audio_path=_make_temp_wav(),
            duration_seconds=0.5,
            sample_rate=22050,
            format="wav",
        )

    mock_provider = AsyncMock()
    mock_provider.synthesize = AsyncMock(side_effect=lambda *_a, **_kw: _fresh_result())

    with patch(
        "app.services.synthesis_service.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        results = await batch_synthesize(
            db_session,
            lines=["Line one.", "Line two.", "Line three."],
            profile_id=profile.id,
        )

    assert len(results) == 3
    for r in results:
        assert "id" in r
        assert "audio_url" in r


async def test_batch_synthesize_skips_empty_lines(db_session: AsyncSession):
    """Empty and whitespace-only lines must be silently skipped."""
    profile = await _make_profile(db_session)

    mock_provider = AsyncMock()
    mock_provider.synthesize = AsyncMock(
        return_value=AudioResult(
            audio_path=_make_temp_wav(),
            duration_seconds=0.5,
            sample_rate=22050,
            format="wav",
        )
    )

    with patch(
        "app.services.synthesis_service.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        results = await batch_synthesize(
            db_session,
            lines=["Valid line.", "", "   ", "Another valid line."],
            profile_id=profile.id,
        )

    assert len(results) == 2


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------

async def test_get_history_empty(db_session: AsyncSession):
    """get_history returns an empty list when no records exist."""
    # Use a unique profile to avoid pollution from other tests
    profile = await _make_profile(db_session, name="Empty History Profile")
    history = await get_history(db_session, profile_id=profile.id)
    assert history == []


async def test_get_history_with_records(db_session: AsyncSession):
    """get_history returns all persisted SynthesisHistory rows."""
    profile = await _make_profile(db_session, name="History Records Profile")

    for i in range(3):
        db_session.add(SynthesisHistory(
            profile_id=profile.id,
            provider_name=profile.provider_name,
            text=f"Test text {i}",
            output_format="wav",
        ))
    await db_session.flush()

    history = await get_history(db_session, profile_id=profile.id)
    assert len(history) >= 3
    assert all(isinstance(h, SynthesisHistory) for h in history)


async def test_get_history_with_profile_filter(db_session: AsyncSession):
    """profile_id filter must return only rows for that profile."""
    profile_a = await _make_profile(db_session, name="Filter Profile A")
    profile_b = await _make_profile(db_session, name="Filter Profile B")

    db_session.add(SynthesisHistory(
        profile_id=profile_a.id, provider_name="kokoro", text="A text", output_format="wav",
    ))
    db_session.add(SynthesisHistory(
        profile_id=profile_b.id, provider_name="kokoro", text="B text", output_format="wav",
    ))
    await db_session.flush()

    history_a = await get_history(db_session, profile_id=profile_a.id)
    assert all(h.profile_id == profile_a.id for h in history_a)
    assert not any(h.profile_id == profile_b.id for h in history_a)
