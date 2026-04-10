"""Persona preset endpoints — CRUD with system defaults."""


import structlog
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession
from app.models.persona_preset import PersonaPreset
from app.schemas.preset import (
    PresetCreate,
    PresetListResponse,
    PresetResponse,
    PresetUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/presets", tags=["presets"])

# System defaults — seeded on first list if not present
SYSTEM_PRESETS = [
    {"name": "Friendly", "description": "Warm and approachable", "speed": 1.0, "pitch": 2.0, "volume": 1.0},
    {"name": "Professional", "description": "Clear and authoritative", "speed": 0.95, "pitch": 0.0, "volume": 1.0},
    {"name": "Energetic", "description": "Upbeat and enthusiastic", "speed": 1.15, "pitch": 5.0, "volume": 1.1},
    {"name": "Calm", "description": "Soothing and relaxed", "speed": 0.85, "pitch": -3.0, "volume": 0.9},
    {"name": "Authoritative", "description": "Commanding and confident", "speed": 0.9, "pitch": -5.0, "volume": 1.15},
    {"name": "Soothing", "description": "Gentle and comforting", "speed": 0.8, "pitch": -2.0, "volume": 0.85},
]


async def _seed_system_presets(db: DbSession) -> None:
    """Seed system presets if they don't exist."""
    result = await db.execute(
        select(PersonaPreset).where(PersonaPreset.is_system == True)  # noqa: E712
    )
    existing = result.scalars().all()
    if existing:
        return

    for p in SYSTEM_PRESETS:
        preset = PersonaPreset(
            name=p["name"],
            description=p["description"],
            speed=p["speed"],
            pitch=p["pitch"],
            volume=p["volume"],
            is_system=True,
        )
        db.add(preset)
    await db.flush()


@router.get("", response_model=PresetListResponse)
async def list_presets(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
) -> PresetListResponse:
    """List all persona presets."""
    logger.info("list_presets_called", limit=limit, offset=offset)
    await _seed_system_presets(db)
    result = await db.execute(
        select(PersonaPreset).order_by(PersonaPreset.name).limit(limit).offset(offset)
    )
    presets = result.scalars().all()
    logger.info("list_presets_returned", count=len(presets))
    return PresetListResponse(
        presets=[PresetResponse.model_validate(p) for p in presets],
        count=len(presets),
    )


@router.post("", response_model=PresetResponse, status_code=status.HTTP_201_CREATED)
async def create_preset(
    data: PresetCreate, db: DbSession, user: CurrentUser
) -> PresetResponse:
    """Create a custom persona preset."""
    logger.info("create_preset_called", name=data.name)
    preset = PersonaPreset(
        name=data.name,
        description=data.description,
        speed=data.speed,
        pitch=data.pitch,
        volume=data.volume,
        is_system=False,
    )
    db.add(preset)
    await db.flush()
    logger.info("preset_created", preset_id=preset.id, name=preset.name)
    return PresetResponse.model_validate(preset)


@router.put("/{preset_id}", response_model=PresetResponse)
async def update_preset(
    preset_id: str, data: PresetUpdate, db: DbSession, user: CurrentUser
) -> PresetResponse:
    """Update a preset (system presets cannot be modified)."""
    logger.info("update_preset_called", preset_id=preset_id)
    result = await db.execute(
        select(PersonaPreset).where(PersonaPreset.id == preset_id)
    )
    preset = result.scalar_one_or_none()
    if preset is None:
        logger.info("update_preset_not_found", preset_id=preset_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")
    if preset.is_system:
        logger.info("update_preset_forbidden_system", preset_id=preset_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify system presets")

    if data.name is not None:
        preset.name = data.name
    if data.description is not None:
        preset.description = data.description
    if data.speed is not None:
        preset.speed = data.speed
    if data.pitch is not None:
        preset.pitch = data.pitch
    if data.volume is not None:
        preset.volume = data.volume
    await db.flush()
    logger.info("preset_updated", preset_id=preset_id)
    return PresetResponse.model_validate(preset)


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preset(
    preset_id: str, db: DbSession, user: CurrentUser
) -> None:
    """Delete a custom preset (system presets cannot be deleted)."""
    logger.info("delete_preset_called", preset_id=preset_id)
    result = await db.execute(
        select(PersonaPreset).where(PersonaPreset.id == preset_id)
    )
    preset = result.scalar_one_or_none()
    if preset is None:
        logger.info("delete_preset_not_found", preset_id=preset_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")
    if preset.is_system:
        logger.info("delete_preset_forbidden_system", preset_id=preset_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete system presets")
    await db.delete(preset)
    await db.flush()
    logger.info("preset_deleted", preset_id=preset_id)
