"""Training service — orchestrates the full training flow."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_sample import AudioSample
from app.models.model_version import ModelVersion
from app.models.training_job import TrainingJob
from app.models.voice_profile import VoiceProfile
from app.services.provider_registry import provider_registry

logger = structlog.get_logger(__name__)


async def start_training(
    db: AsyncSession,
    profile_id: str,
    provider_name: str | None = None,
    config: dict | None = None,
) -> TrainingJob:
    """Start a training job for a profile.

    1. Validates profile exists and has samples
    2. Validates provider supports training
    3. Creates a TrainingJob record
    4. Queues the Celery task
    """
    # Load profile
    result = await db.execute(select(VoiceProfile).where(VoiceProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise ValueError("Profile not found")

    # Resolve provider
    effective_provider = provider_name or profile.provider_name
    try:
        provider = provider_registry.get_provider(effective_provider)
    except ValueError:
        raise ValueError(f"Provider '{effective_provider}' is not available")

    capabilities = await provider.get_capabilities()
    if not capabilities.supports_cloning and not capabilities.supports_fine_tuning:
        raise ValueError(f"Provider '{effective_provider}' does not support training or cloning")

    # Check sample count
    sample_count_result = await db.execute(
        select(func.count()).where(AudioSample.profile_id == profile_id)
    )
    sample_count = sample_count_result.scalar() or 0
    if sample_count == 0:
        raise ValueError("Profile has no audio samples — upload samples before training")

    if capabilities.min_samples_for_cloning > 0 and sample_count < capabilities.min_samples_for_cloning:
        raise ValueError(
            f"Provider '{effective_provider}' requires at least {capabilities.min_samples_for_cloning} "
            f"samples, but only {sample_count} available"
        )

    # Create job
    job = TrainingJob(
        profile_id=profile_id,
        provider_name=effective_provider,
        status="queued",
        progress=0.0,
        config_json=json.dumps(config) if config else None,
    )
    db.add(job)

    # Update profile status
    profile.status = "training"

    # Commit BEFORE dispatching Celery task so the worker can find the job
    await db.commit()

    # Queue Celery task (after commit so job exists in DB)
    from app.tasks.training import train_model

    celery_task = train_model.delay(job.id)
    job.celery_task_id = celery_task.id
    await db.commit()

    logger.info(
        "training_started",
        job_id=job.id,
        profile_id=profile_id,
        provider=effective_provider,
        celery_task_id=celery_task.id,
    )
    return job


async def get_job_status(db: AsyncSession, job_id: str) -> dict:
    """Get training job status with Celery progress info."""
    result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise ValueError("Training job not found")

    response = {
        "id": job.id,
        "profile_id": job.profile_id,
        "provider_name": job.provider_name,
        "status": job.status,
        "progress": job.progress,
        "error_message": job.error_message,
        "result_version_id": job.result_version_id,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat(),
    }

    # Enrich with Celery task metadata if still running
    if job.celery_task_id and job.status in ("queued", "preprocessing", "training"):
        from app.tasks.celery_app import celery_app

        async_result = celery_app.AsyncResult(job.celery_task_id)
        if async_result.state == "PROGRESS" and isinstance(async_result.info, dict):
            response["celery_progress"] = async_result.info

    return response


async def cancel_job(db: AsyncSession, job_id: str) -> TrainingJob:
    """Cancel a running or queued training job."""
    result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise ValueError("Training job not found")

    if job.status in ("completed", "failed", "cancelled"):
        raise ValueError(f"Cannot cancel job with status '{job.status}'")

    celery_task_id = job.celery_task_id

    job.status = "cancelled"
    job.completed_at = datetime.now(UTC)
    await db.commit()

    # Revoke Celery task AFTER commit so DB state is consistent
    if celery_task_id:
        from app.tasks.celery_app import celery_app

        celery_app.control.revoke(celery_task_id, terminate=True)

    # Reset profile status if no other active jobs
    active_result = await db.execute(
        select(func.count()).where(
            TrainingJob.profile_id == job.profile_id,
            TrainingJob.status.in_(("queued", "preprocessing", "training")),
        )
    )
    active_count = active_result.scalar() or 0
    if active_count == 0:
        profile_result = await db.execute(
            select(VoiceProfile).where(VoiceProfile.id == job.profile_id)
        )
        profile = profile_result.scalar_one_or_none()
        if profile and profile.status == "training":
            profile.status = "pending" if profile.active_version_id is None else "ready"

    logger.info("training_cancelled", job_id=job_id)
    return job


async def list_jobs(
    db: AsyncSession,
    profile_id: str | None = None,
    status_filter: str | None = None,
) -> list[TrainingJob]:
    """List training jobs with optional filters."""
    query = select(TrainingJob).order_by(TrainingJob.created_at.desc())
    if profile_id:
        query = query.where(TrainingJob.profile_id == profile_id)
    if status_filter:
        query = query.where(TrainingJob.status == status_filter)

    result = await db.execute(query)
    return list(result.scalars().all())


async def list_versions(db: AsyncSession, profile_id: str) -> list[ModelVersion]:
    """List all model versions for a profile."""
    result = await db.execute(
        select(ModelVersion)
        .where(ModelVersion.profile_id == profile_id)
        .order_by(ModelVersion.version_number.desc())
    )
    return list(result.scalars().all())


async def activate_version(
    db: AsyncSession, profile_id: str, version_id: str
) -> VoiceProfile:
    """Set the active model version for a profile."""
    # Verify version belongs to profile
    result = await db.execute(
        select(ModelVersion).where(
            ModelVersion.id == version_id,
            ModelVersion.profile_id == profile_id,
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise ValueError("Model version not found for this profile")

    result = await db.execute(select(VoiceProfile).where(VoiceProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise ValueError("Profile not found")

    profile.active_version_id = version_id
    if profile.status != "ready":
        profile.status = "ready"
    await db.flush()

    logger.info("version_activated", profile_id=profile_id, version_id=version_id)
    return profile
