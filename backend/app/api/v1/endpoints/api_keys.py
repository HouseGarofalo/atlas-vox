"""API key management endpoints — create, list, revoke."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession
from app.core.security import hash_api_key
from app.models.api_key import ApiKey
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

VALID_SCOPES = {"read", "write", "synthesize", "train", "admin"}


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate, db: DbSession, user: CurrentUser
) -> ApiKeyCreateResponse:
    """Create a new API key. The full key is shown only once."""
    # Validate scopes
    invalid = set(data.scopes) - VALID_SCOPES
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scopes: {', '.join(invalid)}. Valid: {', '.join(sorted(VALID_SCOPES))}",
        )

    # Generate key: avx_ prefix + 48 random chars
    raw_key = f"avx_{secrets.token_urlsafe(36)}"
    key_prefix = raw_key[:12]

    api_key = ApiKey(
        name=data.name,
        key_hash=hash_api_key(raw_key),
        key_prefix=key_prefix,
        scopes=",".join(data.scopes),
        active=True,
    )
    db.add(api_key)
    await db.flush()

    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        key_prefix=key_prefix,
        scopes=data.scopes,
        created_at=api_key.created_at,
    )


@router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(db: DbSession, user: CurrentUser) -> ApiKeyListResponse:
    """List all API keys (masked — only prefix shown)."""
    result = await db.execute(
        select(ApiKey).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return ApiKeyListResponse(
        api_keys=[ApiKeyResponse.model_validate(k) for k in keys],
        count=len(keys),
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str, db: DbSession, user: CurrentUser
) -> None:
    """Revoke (deactivate) an API key."""
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    key = result.scalar_one_or_none()
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    key.active = False
    await db.flush()
