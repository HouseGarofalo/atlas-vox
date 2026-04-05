"""Voice favorites and collections endpoints."""

import uuid

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession
from app.models.voice_favorite import VoiceFavorite

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/favorites", tags=["favorites"])


class FavoriteCreate(BaseModel):
    provider: str = Field(..., min_length=1)
    voice_id: str = Field(..., min_length=1)
    collection_name: str | None = None


@router.get("")
async def list_favorites(
    db: DbSession,
    user: CurrentUser,
    collection: str | None = Query(None),
) -> dict:
    """List all voice favorites, optionally filtered by collection."""
    user_id = user.get("sub", "local-user") if user else "local-user"
    query = select(VoiceFavorite).where(VoiceFavorite.user_id == user_id)
    if collection:
        query = query.where(VoiceFavorite.collection_name == collection)
    query = query.order_by(VoiceFavorite.created_at.desc())

    result = await db.execute(query)
    favorites = result.scalars().all()
    return {
        "favorites": [
            {
                "id": f.id,
                "provider": f.provider,
                "voice_id": f.voice_id,
                "collection_name": f.collection_name,
                "created_at": f.created_at.isoformat(),
            }
            for f in favorites
        ],
        "count": len(favorites),
    }


@router.get("/collections")
async def list_collections(db: DbSession, user: CurrentUser) -> dict:
    """List all named collections for the current user."""
    user_id = user.get("sub", "local-user") if user else "local-user"
    result = await db.execute(
        select(VoiceFavorite.collection_name)
        .where(VoiceFavorite.user_id == user_id)
        .where(VoiceFavorite.collection_name.isnot(None))
        .distinct()
    )
    collections = [row[0] for row in result.all()]
    return {"collections": sorted(collections)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_favorite(data: FavoriteCreate, db: DbSession, user: CurrentUser) -> dict:
    """Add a voice to favorites."""
    user_id = user.get("sub", "local-user") if user else "local-user"

    # Check for duplicates
    existing = await db.execute(
        select(VoiceFavorite).where(
            VoiceFavorite.user_id == user_id,
            VoiceFavorite.provider == data.provider,
            VoiceFavorite.voice_id == data.voice_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Voice already in favorites")

    fav = VoiceFavorite(
        id=str(uuid.uuid4()),
        user_id=user_id,
        provider=data.provider,
        voice_id=data.voice_id,
        collection_name=data.collection_name,
    )
    db.add(fav)
    await db.flush()
    logger.info("favorite_added", provider=data.provider, voice_id=data.voice_id)
    return {
        "id": fav.id,
        "provider": fav.provider,
        "voice_id": fav.voice_id,
        "collection_name": fav.collection_name,
        "created_at": fav.created_at.isoformat(),
    }


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(favorite_id: str, db: DbSession, user: CurrentUser) -> None:
    """Remove a voice from favorites."""
    result = await db.execute(select(VoiceFavorite).where(VoiceFavorite.id == favorite_id))
    fav = result.scalar_one_or_none()
    if not fav:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")
    await db.delete(fav)
    logger.info("favorite_removed", favorite_id=favorite_id)
