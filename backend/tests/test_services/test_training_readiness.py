"""Tests for the training-readiness pre-flight surface (DT-33)."""

from __future__ import annotations

import json as _json
import struct
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_sample import AudioSample
from app.schemas.profile import ProfileCreate
from app.services.profile_service import create_profile
from app.services.training_service import compute_training_readiness


def _make_wav(path: Path) -> None:
    sample_rate, num_channels, bits = 22050, 1, 16
    num_samples = 100
    data_size = num_samples * num_channels * (bits // 8)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, num_channels, sample_rate,
        sample_rate * num_channels * (bits // 8),
        num_channels * (bits // 8), bits,
        b"data", data_size,
    )
    path.write_bytes(header + struct.pack(f"<{num_samples}h", *([0] * num_samples)))


async def _add_sample(
    db: AsyncSession, profile_id: str, tmp_path: Path,
    duration_seconds: float = 10.0,
    analysis: dict | None = None,
    suffix: str = "",
) -> AudioSample:
    wav = tmp_path / f"sample_{profile_id[:6]}{suffix}_{duration_seconds}.wav"
    _make_wav(wav)
    sample = AudioSample(
        profile_id=profile_id,
        filename=wav.name,
        original_filename=wav.name,
        file_path=str(wav),
        format="wav",
        duration_seconds=duration_seconds,
        analysis_json=_json.dumps(analysis) if analysis is not None else None,
    )
    db.add(sample)
    await db.flush()
    return sample


@pytest.fixture
def _mock_capable_provider():
    caps = MagicMock()
    caps.supports_cloning = True
    caps.supports_fine_tuning = True
    caps.min_samples_for_cloning = 1
    p = AsyncMock()
    p.get_capabilities = AsyncMock(return_value=caps)
    return p


async def test_readiness_zero_samples_not_ready(
    db_session: AsyncSession, _mock_capable_provider,
):
    profile = await create_profile(
        db_session,
        ProfileCreate(name="Zero Samples Readiness", provider_name="kokoro"),
    )
    with patch(
        "app.services.training_service.provider_registry.get_provider",
        return_value=_mock_capable_provider,
    ):
        report = await compute_training_readiness(db_session, profile.id)

    assert report["sample_count"] == 0
    assert report["ready"] is False
    assert any("no samples" in b for b in report["blockers"])
    assert report["phoneme_coverage_pct"] == 0.0


async def test_readiness_one_of_two_failed_quality(
    db_session: AsyncSession, tmp_path: Path, _mock_capable_provider,
):
    profile = await create_profile(
        db_session,
        ProfileCreate(name="Mixed Quality Readiness", provider_name="kokoro"),
    )
    await _add_sample(
        db_session, profile.id, tmp_path,
        duration_seconds=6.0,
        analysis={"passed": True},
        suffix="a",
    )
    await _add_sample(
        db_session, profile.id, tmp_path,
        duration_seconds=6.0,
        analysis={"passed": False, "reason": "clipping"},
        suffix="b",
    )

    with patch(
        "app.services.training_service.provider_registry.get_provider",
        return_value=_mock_capable_provider,
    ):
        report = await compute_training_readiness(db_session, profile.id)

    assert report["sample_count"] == 2
    assert report["quality_passed_count"] == 1
    assert len(report["quality_failed_samples"]) == 1
    assert report["quality_failed_samples"][0]["reason"] == "clipping"
    # Has blocker that explicitly names "1 of 2".
    assert any("1 of 2" in b for b in report["blockers"])
    assert report["ready"] is False


async def test_readiness_all_passing_samples_is_ready(
    db_session: AsyncSession, tmp_path: Path, _mock_capable_provider,
):
    profile = await create_profile(
        db_session,
        ProfileCreate(name="All Passing Readiness", provider_name="kokoro"),
    )
    await _add_sample(
        db_session, profile.id, tmp_path,
        duration_seconds=6.0,
        analysis={"passed": True},
        suffix="x",
    )
    await _add_sample(
        db_session, profile.id, tmp_path,
        duration_seconds=6.0,
        analysis={"passed": True},
        suffix="y",
    )

    with patch(
        "app.services.training_service.provider_registry.get_provider",
        return_value=_mock_capable_provider,
    ):
        report = await compute_training_readiness(db_session, profile.id)

    assert report["sample_count"] == 2
    assert report["quality_passed_count"] == 2
    assert report["quality_failed_samples"] == []
    assert report["ready"] is True
    assert report["blockers"] == []


async def test_readiness_under_duration_floor_blocked(
    db_session: AsyncSession, tmp_path: Path, _mock_capable_provider,
):
    profile = await create_profile(
        db_session,
        ProfileCreate(name="Short Audio Readiness", provider_name="kokoro"),
    )
    await _add_sample(
        db_session, profile.id, tmp_path,
        duration_seconds=2.0,
        analysis=None,
        suffix="short",
    )

    with patch(
        "app.services.training_service.provider_registry.get_provider",
        return_value=_mock_capable_provider,
    ):
        report = await compute_training_readiness(db_session, profile.id)

    assert report["ready"] is False
    assert any("audio" in b for b in report["blockers"])
