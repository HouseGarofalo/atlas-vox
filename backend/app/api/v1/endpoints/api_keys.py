"""API key management endpoints — create, list, revoke."""


import secrets

import structlog
from fastapi import APIRouter, HTTPException, Query, status
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

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

VALID_SCOPES = {"read", "write", "synthesize", "train", "admin"}


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate, db: DbSession, user: CurrentUser
) -> ApiKeyCreateResponse:
    """Create a new API key. The full key is shown only once."""
    logger.info("create_api_key_called", name=data.name, scopes=sorted(data.scopes))
    # Validate scopes
    invalid = set(data.scopes) - VALID_SCOPES
    if invalid:
        logger.info("create_api_key_invalid_scopes", invalid_scopes=sorted(invalid))
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

    logger.info("api_key_created", key_id=api_key.id, name=api_key.name, scopes=sorted(data.scopes))
    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        key_prefix=key_prefix,
        scopes=data.scopes,
        created_at=api_key.created_at,
    )


@router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
) -> ApiKeyListResponse:
    """List all API keys (masked — only prefix shown)."""
    logger.info("list_api_keys_called", limit=limit, offset=offset)
    result = await db.execute(
        select(ApiKey).order_by(ApiKey.created_at.desc()).limit(limit).offset(offset)
    )
    keys = result.scalars().all()
    logger.info("list_api_keys_returned", count=len(keys))
    return ApiKeyListResponse(
        api_keys=[ApiKeyResponse.model_validate(k) for k in keys],
        count=len(keys),
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str, db: DbSession, user: CurrentUser
) -> None:
    """Revoke (deactivate) an API key."""
    logger.info("revoke_api_key_called", key_id=key_id)
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    key = result.scalar_one_or_none()
    if key is None:
        logger.info("revoke_api_key_not_found", key_id=key_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    key.active = False
    await db.flush()
    logger.info("api_key_revoked", key_id=key_id, name=key.name)
