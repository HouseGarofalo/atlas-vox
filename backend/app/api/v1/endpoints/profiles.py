"""Voice profile CRUD + model versioning endpoints."""


import json

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from app.core.dependencies import CurrentUser, DbSession
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.profile import (
    ProfileCreate,
    ProfileListResponse,
    ProfileResponse,
    ProfileUpdate,
)
from app.schemas.feedback import ProfileFeedbackSummary
from app.schemas.training import ModelVersionListResponse, ModelVersionResponse
from app.services.feedback_service import aggregate_feedback_for_profile
from app.services.profile_service import (
    create_profile,
    delete_profile,
    get_profile,
    list_profiles_with_counts,
    profile_to_response,
    update_profile,
)
from app.services.training_service import activate_version, list_versions

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=ProfileListResponse)
async def list_all_profiles(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
) -> ProfileListResponse:
    """List all voice profiles."""
    logger.info("list_all_profiles_called", limit=limit, offset=offset)
    rows = await list_profiles_with_counts(db, limit=limit, offset=offset)
    responses = []
    for row in rows:
        profile = row["profile"]
        tags = None
        if profile.tags:
            try:
                tags = json.loads(profile.tags)
            except (ValueError, TypeError):
                tags = None
        responses.append(ProfileResponse(
            id=profile.id,
            name=profile.name,
            description=profile.description,
            language=profile.language,
            provider_name=profile.provider_name,
            voice_id=profile.voice_id,
            status=profile.status,
            tags=tags,
            active_version_id=profile.active_version_id,
            sample_count=row["sample_count"],
            version_count=row["version_count"],
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        ))
    logger.info("list_all_profiles_returned", count=len(responses))
    return ProfileListResponse(profiles=responses, count=len(responses))


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_new_profile(
    data: ProfileCreate, db: DbSession, user: CurrentUser
) -> ProfileResponse:
    """Create a new voice profile."""
    logger.info("create_new_profile_called", name=data.name)
    profile = await create_profile(db, data)
    logger.info("profile_created", profile_id=profile.id, name=profile.name)
    return await profile_to_response(db, profile)


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile_by_id(
    profile_id: str, db: DbSession, user: CurrentUser
) -> ProfileResponse:
    """Get a specific voice profile."""
    logger.info("get_profile_by_id_called", profile_id=profile_id)
    profile = await get_profile(db, profile_id)
    if profile is None:
        logger.info("get_profile_by_id_not_found", profile_id=profile_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return await profile_to_response(db, profile)


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_existing_profile(
    profile_id: str, data: ProfileUpdate, db: DbSession, user: CurrentUser
) -> ProfileResponse:
    """Update a voice profile."""
    logger.info("update_existing_profile_called", profile_id=profile_id)
    profile = await update_profile(db, profile_id, data)
    if profile is None:
        logger.info("update_existing_profile_not_found", profile_id=profile_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    logger.info("profile_updated", profile_id=profile_id)
    return await profile_to_response(db, profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_profile(
    profile_id: str, db: DbSession, user: CurrentUser
):
    """Delete a voice profile."""
    logger.info("delete_existing_profile_called", profile_id=profile_id)
    deleted = await delete_profile(db, profile_id)
    if not deleted:
        logger.info("delete_existing_profile_not_found", profile_id=profile_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    logger.info("profile_deleted", profile_id=profile_id)


# --- Model Versioning ---


@router.get("/{profile_id}/versions", response_model=ModelVersionListResponse)
async def list_profile_versions(
    profile_id: str, db: DbSession, user: CurrentUser
) -> ModelVersionListResponse:
    """List all model versions for a profile."""
    logger.info("list_profile_versions_called", profile_id=profile_id)
    profile = await get_profile(db, profile_id)
    if profile is None:
        logger.info("list_profile_versions_profile_not_found", profile_id=profile_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    versions = await list_versions(db, profile_id)
    logger.info("list_profile_versions_returned", profile_id=profile_id, count=len(versions))
    return ModelVersionListResponse(
        versions=[ModelVersionResponse.model_validate(v) for v in versions],
        count=len(versions),
    )


@router.post("/{profile_id}/activate-version/{version_id}", response_model=ProfileResponse)
async def activate_profile_version(
    profile_id: str, version_id: str, db: DbSession, user: CurrentUser
) -> ProfileResponse:
    """Set the active model version for a profile."""
    logger.info("activate_profile_version_called", profile_id=profile_id, version_id=version_id)
    try:
        profile = await activate_version(db, profile_id, version_id)
        logger.info("profile_version_activated", profile_id=profile_id, version_id=version_id)
        return await profile_to_response(db, profile)
    except (NotFoundError, ValidationError) as e:
        logger.error("activate_profile_version_failed", profile_id=profile_id, version_id=version_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- Regression detector (SL-27) ---


@router.get("/{profile_id}/versions/{version_id}/regression-report")
async def get_regression_report(
    profile_id: str,
    version_id: str,
    db: DbSession,
    user: CurrentUser,
    baseline: str = Query(..., description="Baseline ModelVersion ID to compare against"),
) -> dict:
    """Compute a quality regression report between two model versions.

    Returns the ``RegressionReport`` payload.  ``404`` if either version is
    missing or the ``version_id`` does not belong to ``profile_id``.
    """
    logger.info(
        "get_regression_report_called",
        profile_id=profile_id,
        version_id=version_id,
        baseline=baseline,
    )

    from app.services.regression_detector import detect_regression

    # Validate that version_id belongs to the given profile (defence-in-depth;
    # avoids cross-profile leakage of training metrics via a guessed URL).
    profile = await get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    try:
        report = await detect_regression(
            db,
            new_version_id=version_id,
            baseline_version_id=baseline,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return report.to_dict()


# --- Feedback aggregation (SL-25) ---


@router.get("/{profile_id}/feedback-summary", response_model=ProfileFeedbackSummary)
async def get_profile_feedback_summary(
    profile_id: str, db: DbSession, user: CurrentUser
) -> ProfileFeedbackSummary:
    """Return thumbs up/down counts aggregated across all syntheses for a profile."""
    logger.info("get_profile_feedback_summary_called", profile_id=profile_id)
    profile = await get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    counts = await aggregate_feedback_for_profile(db, profile_id)
    return ProfileFeedbackSummary(
        profile_id=profile_id,
        up=counts["up"],
        down=counts["down"],
        total=counts["total"],
    )


# --- Phoneme coverage (DT-31) ---


@router.get("/{profile_id}/phoneme-coverage")
async def get_phoneme_coverage(
    profile_id: str,
    db: DbSession,
    user: CurrentUser,
    language: str = Query(default="en"),
) -> dict:
    """Return phoneme coverage for a training profile's transcripts."""
    profile = await get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    from app.services.phoneme_coverage import analyze_profile_coverage

    report = await analyze_profile_coverage(db, profile_id, language=language)
    return report.to_dict()


# --- Per-profile quality dashboard (VQ-36) ---


@router.get("/{profile_id}/quality-dashboard")
async def get_quality_dashboard(
    profile_id: str,
    db: DbSession,
    user: CurrentUser,
    wer_limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    """Aggregate every available quality signal for a profile in one payload.

    Combines:
      - WER time-series from Whisper-check (SL-28)
      - Per-version metrics (SL-27 regression detector)
      - Rating distribution (SL-25 thumbs up/down)
      - Training-sample health breakdown (audio_quality validator)

    Returns a scalar overall_score plus time-series data for charts.
    404 when the profile does not exist.
    """
    from app.services.quality_dashboard import build_quality_dashboard

    try:
        report = await build_quality_dashboard(
            db, profile_id, wer_limit=wer_limit,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    return report.to_dict()


# --- Active-learning sample recommender (SL-29) ---


@router.get("/{profile_id}/recommended-samples")
async def get_recommended_samples(
    profile_id: str,
    db: DbSession,
    user: CurrentUser,
    count: int = Query(default=10, ge=1, le=30),
    language: str = Query(default="en"),
) -> dict:
    """Recommend the next ``count`` sentences to record for max coverage.

    Uses greedy set-cover over a curated sentence bank (CMU Arctic +
    phoneme-targeted extras) to maximally fill the profile's remaining
    phoneme gaps. Sentences the user has already recorded are skipped.
    """
    profile = await get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    from app.services.sample_recommender import recommend_next_samples

    recommendation = await recommend_next_samples(
        db, profile_id, count=count, language=language,
    )
    return recommendation.to_dict()


# --- Training readiness (DT-33) ---


@router.get("/{profile_id}/training-readiness")
async def get_training_readiness(
    profile_id: str, db: DbSession, user: CurrentUser,
) -> dict:
    """Return a pre-flight readiness report for starting training on a profile."""
    profile = await get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    from app.services.training_service import compute_training_readiness

    report = await compute_training_readiness(db, profile_id)
    return report
