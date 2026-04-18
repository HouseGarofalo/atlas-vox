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
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Profile")

    # Resolve provider
    effective_provider = provider_name or profile.provider_name
    try:
        provider = provider_registry.get_provider(effective_provider)
    except ValueError:
        from app.core.exceptions import ProviderError
        raise ProviderError(effective_provider, "is not available")

    capabilities = await provider.get_capabilities()
    if not capabilities.supports_cloning and not capabilities.supports_fine_tuning:
        from app.core.exceptions import ValidationError
        raise ValidationError(f"Provider '{effective_provider}' does not support training or cloning")

    # Load samples so we can pre-flight: count, total duration, and quality
    # pass-rate checks must all happen before we enqueue a Celery job that
    # would otherwise fail silently in the worker.
    sample_rows = (
        await db.execute(
            select(AudioSample).where(AudioSample.profile_id == profile_id)
        )
    ).scalars().all()
    sample_count = len(sample_rows)
    if sample_count == 0:
        from app.core.exceptions import ValidationError
        raise ValidationError("Profile has no audio samples — upload samples before training")

    if capabilities.min_samples_for_cloning > 0 and sample_count < capabilities.min_samples_for_cloning:
        from app.core.exceptions import ValidationError
        raise ValidationError(
            f"Provider '{effective_provider}' requires at least {capabilities.min_samples_for_cloning} "
            f"samples, but only {sample_count} available"
        )

    # Duration floor — cloning on <5 s of audio produces garbage; enforce
    # a realistic minimum before wasting a worker slot.
    total_duration = sum((s.duration_seconds or 0.0) for s in sample_rows)
    MIN_TOTAL_DURATION_S = 5.0
    if total_duration < MIN_TOTAL_DURATION_S:
        from app.core.exceptions import ValidationError
        raise ValidationError(
            f"Profile has only {total_duration:.1f}s of audio total; "
            f"at least {MIN_TOTAL_DURATION_S:.0f}s required before training."
        )

    # Quality gate — if every sample has been analysed and failed quality
    # we refuse to train on known-bad data.  Samples without an analysis_json
    # are treated as unknown (allowed) so existing flows don't regress.
    bad_samples: list[str] = []
    any_analysed = False
    for s in sample_rows:
        if not s.analysis_json:
            continue
        any_analysed = True
        try:
            analysis = json.loads(s.analysis_json) if isinstance(s.analysis_json, str) else s.analysis_json
        except (ValueError, TypeError):
            continue
        if isinstance(analysis, dict) and analysis.get("passed") is False:
            bad_samples.append(s.original_filename or s.filename)
    if any_analysed and len(bad_samples) == sample_count:
        from app.core.exceptions import ValidationError
        raise ValidationError(
            "All samples failed the audio-quality check. "
            "Re-record or fix the following before training: "
            + ", ".join(bad_samples[:5])
            + (f" (and {len(bad_samples) - 5} more)" if len(bad_samples) > 5 else "")
        )

    logger.info(
        "training_validation_passed",
        profile_id=profile_id,
        provider=effective_provider,
        sample_count=sample_count,
        total_duration_s=round(total_duration, 2),
        bad_quality_samples=len(bad_samples),
        supports_cloning=capabilities.supports_cloning,
        supports_fine_tuning=capabilities.supports_fine_tuning,
    )

    # Snapshot profile status so we can revert if Celery dispatch fails.
    previous_profile_status = profile.status

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

    # Flush to generate the job ID, then dispatch Celery and commit atomically.
    # If Celery is unreachable or rejects the task we must not leave the DB
    # in a "training" state with an orphaned job that no worker will ever run.
    await db.flush()

    from app.tasks.training import train_model

    try:
        celery_task = train_model.delay(job.id)
    except Exception as exc:  # kombu/celery raise a range of transport errors
        logger.error(
            "training_dispatch_failed",
            job_id=job.id,
            profile_id=profile_id,
            provider=effective_provider,
            error=str(exc),
        )
        # Revert: mark job failed, restore profile status, persist.
        job.status = "failed"
        job.error_message = f"Failed to enqueue training task: {exc}"
        job.completed_at = datetime.now(UTC)
        profile.status = previous_profile_status
        await db.flush()
        from app.core.exceptions import ProviderError

        raise ProviderError(
            effective_provider,
            "training queue is unavailable — please try again shortly",
        ) from exc

    job.celery_task_id = celery_task.id

    # Flush ensures celery_task_id is set before auto-commit
    await db.flush()

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
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Training job")

    logger.info(
        "job_status_queried",
        job_id=job_id,
        status=job.status,
        progress=job.progress,
        profile_id=job.profile_id,
        provider=job.provider_name,
    )

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
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Training job")

    if job.status in ("completed", "failed", "cancelled"):
        from app.core.exceptions import ValidationError
        raise ValidationError(f"Cannot cancel job with status '{job.status}'")

    celery_task_id = job.celery_task_id

    job.status = "cancelled"
    job.completed_at = datetime.now(UTC)
    await db.flush()

    # Revoke Celery task AFTER flush so DB state is consistent
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
    limit: int = 50,
    offset: int = 0,
) -> list[TrainingJob]:
    """List training jobs with optional filters and pagination."""
    query = select(TrainingJob).order_by(TrainingJob.created_at.desc())
    if profile_id:
        query = query.where(TrainingJob.profile_id == profile_id)
    if status_filter:
        query = query.where(TrainingJob.status == status_filter)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    jobs = list(result.scalars().all())
    logger.info(
        "jobs_listed",
        count=len(jobs),
        profile_id=profile_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return jobs


async def list_versions(db: AsyncSession, profile_id: str) -> list[ModelVersion]:
    """List all model versions for a profile."""
    result = await db.execute(
        select(ModelVersion)
        .where(ModelVersion.profile_id == profile_id)
        .order_by(ModelVersion.version_number.desc())
    )
    versions = list(result.scalars().all())
    logger.info("versions_listed", profile_id=profile_id, count=len(versions))
    return versions


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
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Model version")

    result = await db.execute(select(VoiceProfile).where(VoiceProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Profile")

    profile.active_version_id = version_id
    if profile.status != "ready":
        profile.status = "ready"
    await db.flush()

    logger.info("version_activated", profile_id=profile_id, version_id=version_id)
    return profile
