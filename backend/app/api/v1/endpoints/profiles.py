"""Voice profile CRUD + model versioning endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.profile import (
    ProfileCreate,
    ProfileListResponse,
    ProfileResponse,
    ProfileUpdate,
)
from app.schemas.training import ModelVersionListResponse, ModelVersionResponse
from app.services.profile_service import (
    create_profile,
    delete_profile,
    get_profile,
    list_profiles,
    profile_to_response,
    update_profile,
)
from app.services.training_service import activate_version, list_versions

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=ProfileListResponse)
async def list_all_profiles(db: DbSession, user: CurrentUser) -> ProfileListResponse:
    """List all voice profiles."""
    profiles = await list_profiles(db)
    responses = [await profile_to_response(db, p) for p in profiles]
    return ProfileListResponse(profiles=responses, count=len(profiles))


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_new_profile(
    data: ProfileCreate, db: DbSession, user: CurrentUser
) -> ProfileResponse:
    """Create a new voice profile."""
    profile = await create_profile(db, data)
    return await profile_to_response(db, profile)


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile_by_id(
    profile_id: str, db: DbSession, user: CurrentUser
) -> ProfileResponse:
    """Get a specific voice profile."""
    profile = await get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return await profile_to_response(db, profile)


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_existing_profile(
    profile_id: str, data: ProfileUpdate, db: DbSession, user: CurrentUser
) -> ProfileResponse:
    """Update a voice profile."""
    profile = await update_profile(db, profile_id, data)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return await profile_to_response(db, profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_profile(
    profile_id: str, db: DbSession, user: CurrentUser
) -> None:
    """Delete a voice profile."""
    deleted = await delete_profile(db, profile_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")


# --- Model Versioning ---


@router.get("/{profile_id}/versions", response_model=ModelVersionListResponse)
async def list_profile_versions(
    profile_id: str, db: DbSession, user: CurrentUser
) -> ModelVersionListResponse:
    """List all model versions for a profile."""
    profile = await get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    versions = await list_versions(db, profile_id)
    return ModelVersionListResponse(
        versions=[ModelVersionResponse.model_validate(v) for v in versions],
        count=len(versions),
    )


@router.post("/{profile_id}/activate-version/{version_id}", response_model=ProfileResponse)
async def activate_profile_version(
    profile_id: str, version_id: str, db: DbSession, user: CurrentUser
) -> ProfileResponse:
    """Set the active model version for a profile."""
    try:
        profile = await activate_version(db, profile_id, version_id)
        return await profile_to_response(db, profile)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
