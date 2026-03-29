"""Voice profile business logic."""

from __future__ import annotations

import json
import uuid

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_sample import AudioSample
from app.models.model_version import ModelVersion
from app.models.training_job import TrainingJob
from app.models.voice_profile import VoiceProfile
from app.schemas.profile import ProfileCreate, ProfileResponse, ProfileUpdate

logger = structlog.get_logger(__name__)


async def create_profile(db: AsyncSession, data: ProfileCreate) -> VoiceProfile:
    """Create a new voice profile.

    If ``voice_id`` is provided the profile uses a pre-built voice and is
    immediately ready for synthesis (no training required).
    """
    profile = VoiceProfile(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        language=data.language,
        provider_name=data.provider_name,
        voice_id=data.voice_id,
        status="ready" if data.voice_id else "pending",
        tags=json.dumps(data.tags) if data.tags else None,
    )
    db.add(profile)
    await db.flush()
    logger.info(
        "profile_created",
        profile_id=profile.id,
        name=profile.name,
        provider=profile.provider_name,
        language=profile.language,
        status=profile.status,
    )
    return profile


async def get_profile(db: AsyncSession, profile_id: str) -> VoiceProfile | None:
    """Get a profile by ID."""
    result = await db.execute(select(VoiceProfile).where(VoiceProfile.id == profile_id))
    return result.scalar_one_or_none()


async def list_profiles(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> list[VoiceProfile]:
    """List all profiles with optional pagination."""
    result = await db.execute(
        select(VoiceProfile)
        .order_by(VoiceProfile.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    profiles = list(result.scalars().all())
    logger.info("profiles_listed", count=len(profiles), limit=limit, offset=offset)
    return profiles


async def list_profiles_with_counts(
    db: AsyncSession, limit: int = 50, offset: int = 0
) -> list[dict]:
    """List profiles with sample_count and version_count pre-computed in a single query."""
    # Subqueries for counts
    sample_count_sq = (
        select(func.count(AudioSample.id))
        .where(AudioSample.profile_id == VoiceProfile.id)
        .correlate(VoiceProfile)
        .scalar_subquery()
        .label("sample_count")
    )
    version_count_sq = (
        select(func.count(ModelVersion.id))
        .where(ModelVersion.profile_id == VoiceProfile.id)
        .correlate(VoiceProfile)
        .scalar_subquery()
        .label("version_count")
    )

    query = (
        select(VoiceProfile, sample_count_sq, version_count_sq)
        .order_by(VoiceProfile.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    rows = result.all()

    profiles = [
        {
            "profile": row[0],
            "sample_count": row[1] or 0,
            "version_count": row[2] or 0,
        }
        for row in rows
    ]
    logger.info("profiles_listed_with_counts", count=len(profiles), limit=limit, offset=offset)
    return profiles


async def update_profile(
    db: AsyncSession, profile_id: str, data: ProfileUpdate
) -> VoiceProfile | None:
    """Update a profile."""
    profile = await get_profile(db, profile_id)
    if profile is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    if "tags" in update_data and update_data["tags"] is not None:
        update_data["tags"] = json.dumps(update_data["tags"])

    changed_fields = list(update_data.keys())
    for key, value in update_data.items():
        setattr(profile, key, value)

    await db.flush()
    logger.info("profile_updated", profile_id=profile_id, changed_fields=changed_fields)
    return profile


async def delete_profile(db: AsyncSession, profile_id: str) -> bool:
    """Delete a profile and all related data, revoking any active training jobs."""
    profile = await get_profile(db, profile_id)
    if profile is None:
        return False

    # Revoke any active Celery training tasks before cascade-deleting
    result = await db.execute(
        select(TrainingJob).where(
            TrainingJob.profile_id == profile_id,
            TrainingJob.status.in_(("queued", "preprocessing", "training")),
        )
    )
    active_jobs = result.scalars().all()
    if active_jobs:
        try:
            from app.tasks.celery_app import celery_app

            for job in active_jobs:
                if job.celery_task_id:
                    celery_app.control.revoke(job.celery_task_id, terminate=True)
                    logger.info("revoked_training_task", job_id=job.id, celery_task_id=job.celery_task_id)
        except Exception:
            logger.warning("celery_revoke_failed", profile_id=profile_id, exc_info=True)

    await db.delete(profile)
    await db.flush()
    logger.info(
        "profile_deleted",
        profile_id=profile_id,
        active_jobs_cancelled=len(active_jobs),
    )
    return True


async def profile_to_response(db: AsyncSession, profile: VoiceProfile) -> ProfileResponse:
    """Convert a VoiceProfile ORM object to a response schema."""
    tags = None
    if profile.tags:
        try:
            tags = json.loads(profile.tags)
        except (ValueError, TypeError):
            tags = None

    # Use count queries to avoid lazy-loading relationships
    sample_count_result = await db.execute(
        select(func.count()).where(AudioSample.profile_id == profile.id)
    )
    version_count_result = await db.execute(
        select(func.count()).where(ModelVersion.profile_id == profile.id)
    )

    return ProfileResponse(
        id=profile.id,
        name=profile.name,
        description=profile.description,
        language=profile.language,
        provider_name=profile.provider_name,
        voice_id=profile.voice_id,
        status=profile.status,
        tags=tags,
        active_version_id=profile.active_version_id,
        sample_count=sample_count_result.scalar() or 0,
        version_count=version_count_result.scalar() or 0,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
