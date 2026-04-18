"""Tests for SL-27 regression detector."""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_version import ModelVersion
from app.providers.base import AudioResult
from app.schemas.profile import ProfileCreate
from app.services.profile_service import create_profile
from app.services.regression_detector import (
    SIMILARITY_DROP_THRESHOLD,
    WER_REGRESSION_DELTA,
    detect_regression,
)


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


async def _seed_profile_with_versions(db: AsyncSession, name: str):
    profile = await create_profile(
        db, ProfileCreate(name=name, provider_name="kokoro", voice_id="af_heart")
    )
    baseline = ModelVersion(
        profile_id=profile.id,
        version_number=1,
        provider_model_id="baseline-voice",
    )
    new = ModelVersion(
        profile_id=profile.id,
        version_number=2,
        provider_model_id="new-voice",
    )
    db.add_all([baseline, new])
    await db.flush()
    return profile, baseline, new


def _mock_provider_factory(wav_path: Path) -> AsyncMock:
    audio = AudioResult(
        audio_path=wav_path,
        duration_seconds=1.0,
        sample_rate=22050,
        format="wav",
    )
    provider = AsyncMock()
    provider.synthesize = AsyncMock(return_value=audio)
    return provider


# ---------------------------------------------------------------------------
# No-regression path — WER equal across versions, similarity high
# ---------------------------------------------------------------------------

async def test_detect_regression_no_regression(db_session: AsyncSession):
    _, baseline, new = await _seed_profile_with_versions(db_session, "No Regression")

    wav = _temp_wav()
    provider = _mock_provider_factory(wav)

    # Whisper returns the phrase exactly → WER == 0 for both versions.
    async def _fake_transcribe(path):
        # Decide which transcript to emit based on the call order — not
        # needed here because both versions yield perfect transcripts.
        return "the quick brown fox jumps over the lazy dog."

    with patch(
        "app.services.regression_detector.provider_registry.get_provider",
        return_value=provider,
    ), patch(
        "app.services.whisper_transcriber.transcribe",
        new=AsyncMock(side_effect=_fake_transcribe),
    ), patch(
        "app.services.regression_detector._speaker_similarity_sync",
        return_value=0.98,  # very high similarity
    ), patch(
        "app.services.regression_detector.get_eval_phrases",
        return_value=["the quick brown fox jumps over the lazy dog."],
    ):
        report = await detect_regression(
            db_session,
            new_version_id=new.id,
            baseline_version_id=baseline.id,
        )

    assert report.is_regression is False
    assert report.wer_new == pytest.approx(0.0)
    assert report.wer_baseline == pytest.approx(0.0)
    assert report.speaker_sim_score == pytest.approx(0.98)
    assert report.delta_metrics["wer_delta"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Regression flagged — WER gap above threshold
# ---------------------------------------------------------------------------

async def test_detect_regression_flags_wer_gap(db_session: AsyncSession):
    _, baseline, new = await _seed_profile_with_versions(db_session, "WER Gap")

    wav = _temp_wav()
    provider = _mock_provider_factory(wav)

    # Track which version is currently being synthesised by snooping on the
    # voice_id passed to provider.synthesize.  The detector synthesises all
    # new-version phrases first, then all baseline-version phrases (sequential),
    # so we can key off that order via a simple counter.
    call_log: list[str] = []

    async def _fake_synth(text, voice_id, settings):
        call_log.append(voice_id)
        from app.providers.base import AudioResult
        return AudioResult(audio_path=wav, duration_seconds=1.0, sample_rate=22050, format="wav")

    provider.synthesize = AsyncMock(side_effect=_fake_synth)

    phrase = "the quick brown fox"

    async def _fake_transcribe(path):
        # First half of calls are the new version; emit a garbled transcript.
        # Second half are the baseline; emit a perfect transcript.
        n_new = call_log.count("new-voice")
        n_base = call_log.count("baseline-voice")
        # Each synth call creates a transcription target; we rely on call order:
        # New-voice transcripts come first, so while any new-voice calls remain untranscribed, return garbled.
        if n_new > 0 and _fake_transcribe.counter < n_new:
            _fake_transcribe.counter += 1
            return "totally wrong words here"
        _fake_transcribe.counter += 1
        return phrase

    _fake_transcribe.counter = 0

    with patch(
        "app.services.regression_detector.provider_registry.get_provider",
        return_value=provider,
    ), patch(
        "app.services.whisper_transcriber.transcribe",
        new=AsyncMock(side_effect=_fake_transcribe),
    ), patch(
        "app.services.regression_detector._speaker_similarity_sync",
        return_value=0.95,  # good similarity — regression must come from WER
    ), patch(
        "app.services.regression_detector.get_eval_phrases",
        return_value=[phrase],
    ):
        report = await detect_regression(
            db_session,
            new_version_id=new.id,
            baseline_version_id=baseline.id,
        )

    assert report.is_regression is True
    # New-version WER should be far worse than baseline (near-perfect)
    assert report.wer_new > report.wer_baseline
    assert report.delta_metrics["wer_delta"] > WER_REGRESSION_DELTA


async def test_detect_regression_flags_speaker_drift(db_session: AsyncSession):
    _, baseline, new = await _seed_profile_with_versions(db_session, "Speaker Drift")

    wav = _temp_wav()
    provider = _mock_provider_factory(wav)

    with patch(
        "app.services.regression_detector.provider_registry.get_provider",
        return_value=provider,
    ), patch(
        "app.services.whisper_transcriber.transcribe",
        new=AsyncMock(return_value="the quick brown fox"),
    ), patch(
        "app.services.regression_detector._speaker_similarity_sync",
        # Way below the 1.0 - SIMILARITY_DROP_THRESHOLD floor → flags regression.
        return_value=0.40,
    ), patch(
        "app.services.regression_detector.get_eval_phrases",
        return_value=["the quick brown fox"],
    ):
        report = await detect_regression(
            db_session,
            new_version_id=new.id,
            baseline_version_id=baseline.id,
        )

    assert report.is_regression is True
    assert report.speaker_sim_score < (1.0 - SIMILARITY_DROP_THRESHOLD)


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

async def test_detect_regression_missing_version_raises(db_session: AsyncSession):
    from app.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await detect_regression(
            db_session,
            new_version_id="does-not-exist",
            baseline_version_id="also-missing",
        )


async def test_detect_regression_same_version_is_rejected(db_session: AsyncSession):
    _, baseline, _ = await _seed_profile_with_versions(db_session, "Same Version")

    with pytest.raises(ValueError):
        await detect_regression(
            db_session,
            new_version_id=baseline.id,
            baseline_version_id=baseline.id,
        )
