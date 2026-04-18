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
