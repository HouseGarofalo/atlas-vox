"""Tests for the training service layer."""

from __future__ import annotations

import struct
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_sample import AudioSample
from app.models.model_version import ModelVersion
from app.models.training_job import TrainingJob
from app.models.voice_profile import VoiceProfile
from app.core.exceptions import ValidationError, NotFoundError
from app.schemas.profile import ProfileCreate
from app.services.profile_service import create_profile
from app.services.training_service import (
    activate_version,
    cancel_job,
    get_job_status,
    list_jobs,
    list_versions,
    start_training,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_profile(db: AsyncSession, name: str = "Train Profile", provider: str = "elevenlabs") -> VoiceProfile:
    return await create_profile(db, ProfileCreate(name=name, provider_name=provider))


def _make_wav(path: Path) -> None:
    sample_rate, num_channels, bits = 22050, 1, 16
    num_samples = sample_rate
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


async def _add_sample(db: AsyncSession, profile_id: str, tmp_path: Path) -> AudioSample:
    wav = tmp_path / f"sample_{profile_id[:6]}.wav"
    _make_wav(wav)
    sample = AudioSample(
        profile_id=profile_id,
        filename=wav.name,
        original_filename=wav.name,
        file_path=str(wav),
        format="wav",
        file_size_bytes=wav.stat().st_size,
    )
    db.add(sample)
    await db.flush()
    return sample


def _mock_training_provider() -> AsyncMock:
    """Build a mock provider that supports both cloning and fine-tuning."""
    capabilities = MagicMock()
    capabilities.supports_cloning = True
    capabilities.supports_fine_tuning = True
    capabilities.min_samples_for_cloning = 1

    provider = AsyncMock()
    provider.get_capabilities = AsyncMock(return_value=capabilities)
    return provider


# ---------------------------------------------------------------------------
# start_training — validation errors (existing)
# ---------------------------------------------------------------------------

async def test_start_training_no_profile(db_session: AsyncSession):
    with pytest.raises(NotFoundError, match="not found"):
        await start_training(db_session, profile_id="nonexistent-profile-id")


async def test_start_training_no_samples(db_session: AsyncSession):
    """Profile exists but has zero samples."""
    profile = await _make_profile(db_session, provider="elevenlabs")

    mock_capabilities = MagicMock()
    mock_capabilities.supports_cloning = True
    mock_capabilities.supports_fine_tuning = False
    mock_capabilities.min_samples_for_cloning = 0

    mock_provider = AsyncMock()
    mock_provider.get_capabilities = AsyncMock(return_value=mock_capabilities)

    with patch(
        "app.services.training_service.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        with pytest.raises(ValidationError, match="no audio samples"):
            await start_training(db_session, profile_id=profile.id)


async def test_start_training_provider_no_training(db_session: AsyncSession):
    """Provider that supports neither cloning nor fine-tuning should raise."""
    profile = await _make_profile(db_session, provider="kokoro")

    mock_capabilities = MagicMock()
    mock_capabilities.supports_cloning = False
    mock_capabilities.supports_fine_tuning = False
    mock_capabilities.min_samples_for_cloning = 0

    mock_provider = AsyncMock()
    mock_provider.get_capabilities = AsyncMock(return_value=mock_capabilities)

    with patch(
        "app.services.training_service.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        with pytest.raises(ValidationError, match="training|cloning"):
            await start_training(db_session, profile_id=profile.id)


# ---------------------------------------------------------------------------
# start_training — success path
# ---------------------------------------------------------------------------

async def test_start_training_success(db_session: AsyncSession, tmp_path: Path):
    """start_training creates a queued TrainingJob with celery_task_id."""
    profile = await _make_profile(db_session, provider="elevenlabs")
    await _add_sample(db_session, profile.id, tmp_path)

    mock_provider = _mock_training_provider()
    fake_celery_task = MagicMock()
    fake_celery_task.id = "celery-task-abc-123"

    with patch(
        "app.services.training_service.provider_registry.get_provider",
        return_value=mock_provider,
    ):
        with patch(
            "app.tasks.training.train_model.delay",
            return_value=fake_celery_task,
        ) as mock_delay:
            job = await start_training(db_session, profile_id=profile.id)

    assert job is not None
    assert job.profile_id == profile.id
    assert job.status == "queued"
    assert job.celery_task_id == "celery-task-abc-123"
    mock_delay.assert_called_once_with(job.id)


# ---------------------------------------------------------------------------
# get_job_status
# ---------------------------------------------------------------------------

async def test_get_job_status_success(db_session: AsyncSession):
    """get_job_status returns dict with expected keys for an existing job."""
    profile = await _make_profile(db_session)
    job = TrainingJob(
        profile_id=profile.id,
        provider_name="elevenlabs",
        status="queued",
        progress=0.0,
    )
    db_session.add(job)
    await db_session.flush()

    status = await get_job_status(db_session, job_id=job.id)

    assert status["id"] == job.id
    assert status["profile_id"] == profile.id
    assert status["provider_name"] == "elevenlabs"
    assert status["status"] == "queued"
    assert "progress" in status
    assert "created_at" in status
    assert "error_message" in status
    assert "result_version_id" in status


async def test_get_job_status_not_found(db_session: AsyncSession):
    """Nonexistent job_id must raise NotFoundError."""
    with pytest.raises(NotFoundError, match="not found"):
        await get_job_status(db_session, job_id="no-such-job-id")


# ---------------------------------------------------------------------------
# activate_version
# ---------------------------------------------------------------------------

async def test_activate_version_success(db_session: AsyncSession):
    """activate_version sets profile.active_version_id and status to ready."""
    profile = await _make_profile(db_session)
    version = ModelVersion(
        profile_id=profile.id,
        version_number=1,
        provider_model_id="voice-xyz",
    )
    db_session.add(version)
    await db_session.flush()

    updated_profile = await activate_version(db_session, profile_id=profile.id, version_id=version.id)

    assert updated_profile.active_version_id == version.id
    assert updated_profile.status == "ready"


async def test_activate_version_wrong_profile(db_session: AsyncSession):
    """A version belonging to a different profile must raise NotFoundError."""
    profile_a = await _make_profile(db_session, name="Profile A")
    profile_b = await _make_profile(db_session, name="Profile B")

    version_for_b = ModelVersion(
        profile_id=profile_b.id,
        version_number=1,
        provider_model_id="voice-b",
    )
    db_session.add(version_for_b)
    await db_session.flush()

    with pytest.raises(NotFoundError, match="not found"):
        await activate_version(db_session, profile_id=profile_a.id, version_id=version_for_b.id)


async def test_activate_version_not_found(db_session: AsyncSession):
    """Nonexistent version_id must raise NotFoundError."""
    profile = await _make_profile(db_session)
    with pytest.raises(NotFoundError, match="not found"):
        await activate_version(db_session, profile_id=profile.id, version_id="no-such-version")


# ---------------------------------------------------------------------------
# list_jobs
# ---------------------------------------------------------------------------

async def test_list_jobs_empty(db_session: AsyncSession):
    jobs = await list_jobs(db_session)
    assert isinstance(jobs, list)


async def test_list_jobs_with_filter(db_session: AsyncSession):
    profile = await _make_profile(db_session)

    queued_job = TrainingJob(
        profile_id=profile.id,
        provider_name="elevenlabs",
        status="queued",
        progress=0.0,
    )
    completed_job = TrainingJob(
        profile_id=profile.id,
        provider_name="elevenlabs",
        status="completed",
        progress=1.0,
    )
    db_session.add(queued_job)
    db_session.add(completed_job)
    await db_session.flush()

    queued = await list_jobs(db_session, status_filter="queued")
    completed = await list_jobs(db_session, status_filter="completed")

    assert all(j.status == "queued" for j in queued)
    assert all(j.status == "completed" for j in completed)


async def test_list_jobs_by_profile(db_session: AsyncSession):
    profile_a = await _make_profile(db_session, name="Profile A")
    profile_b = await _make_profile(db_session, name="Profile B")

    db_session.add(TrainingJob(profile_id=profile_a.id, provider_name="elevenlabs", status="queued", progress=0.0))
    db_session.add(TrainingJob(profile_id=profile_b.id, provider_name="elevenlabs", status="queued", progress=0.0))
    await db_session.flush()

    jobs_a = await list_jobs(db_session, profile_id=profile_a.id)
    assert all(j.profile_id == profile_a.id for j in jobs_a)
    assert not any(j.profile_id == profile_b.id for j in jobs_a)


# ---------------------------------------------------------------------------
# cancel_job
# ---------------------------------------------------------------------------

async def test_cancel_job_not_found(db_session: AsyncSession):
    with pytest.raises(NotFoundError, match="not found"):
        await cancel_job(db_session, job_id="nonexistent-job-id")


async def test_cancel_completed_job(db_session: AsyncSession):
    profile = await _make_profile(db_session)
    from datetime import UTC, datetime
    job = TrainingJob(
        profile_id=profile.id,
        provider_name="elevenlabs",
        status="completed",
        progress=1.0,
        completed_at=datetime.now(UTC),
    )
    db_session.add(job)
    await db_session.flush()

    with pytest.raises(ValidationError, match="cancel"):
        await cancel_job(db_session, job_id=job.id)


async def test_cancel_failed_job(db_session: AsyncSession):
    profile = await _make_profile(db_session)
    job = TrainingJob(
        profile_id=profile.id,
        provider_name="elevenlabs",
        status="failed",
        progress=0.0,
    )
    db_session.add(job)
    await db_session.flush()

    with pytest.raises(ValidationError, match="cancel"):
        await cancel_job(db_session, job_id=job.id)


async def test_cancel_queued_job(db_session: AsyncSession):
    profile = await _make_profile(db_session)
    job = TrainingJob(
        profile_id=profile.id,
        provider_name="elevenlabs",
        status="queued",
        progress=0.0,
    )
    db_session.add(job)
    await db_session.flush()
    job_id = job.id

    with patch("app.tasks.celery_app.celery_app") as mock_celery:
        mock_celery.control.revoke = MagicMock()
        cancelled = await cancel_job(db_session, job_id=job_id)

    assert cancelled.status == "cancelled"


# ---------------------------------------------------------------------------
# list_versions
# ---------------------------------------------------------------------------

async def test_list_versions_empty(db_session: AsyncSession):
    profile = await _make_profile(db_session)
    versions = await list_versions(db_session, profile_id=profile.id)
    assert versions == []


async def test_list_versions(db_session: AsyncSession):
    profile = await _make_profile(db_session)
    version = ModelVersion(
        profile_id=profile.id,
        version_number=1,
        provider_model_id="voice-abc",
    )
    db_session.add(version)
    await db_session.flush()

    versions = await list_versions(db_session, profile_id=profile.id)
    assert len(versions) >= 1
    assert versions[0].provider_model_id == "voice-abc"
