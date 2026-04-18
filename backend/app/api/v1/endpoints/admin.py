"""Admin API endpoints — system settings, diagnostics, backup/restore."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.core.config import settings as app_settings
from app.core.dependencies import CurrentUser, DbSession, require_scope
from app.core.encryption import decrypt_value, encrypt_value
from app.models.provider import Provider
from app.models.synthesis_history import SynthesisHistory
from app.models.voice_profile import VoiceProfile
from app.schemas.admin import (
    BackupResponse,
    BulkSettingsUpdate,
    RestoreRequest,
    SystemInfoResponse,
    SystemSettingResponse,
    SystemSettingUpdate,
)
from app.services.system_settings_service import SystemSettingsService

logger = structlog.get_logger("atlas_vox.api.admin")

router = APIRouter(prefix="/admin", tags=["admin"])

# Track startup time for uptime calculation
_startup_time = time.monotonic()


# ── Settings CRUD ────────────────────────────────────────────────────────


@router.get("/settings", response_model=list[SystemSettingResponse])
async def list_settings(
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
    category: str | None = Query(None, description="Filter by category"),
):
    """List all system settings (secrets are masked)."""
    return await SystemSettingsService.get_all(db, category=category)


@router.get("/settings/{category}", response_model=list[SystemSettingResponse])
async def list_category_settings(
    category: str,
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
):
    """List settings for a specific category."""
    return await SystemSettingsService.get_all(db, category=category)


@router.get(
    "/settings/{category}/{key}", response_model=SystemSettingResponse | None
)
async def get_setting(
    category: str,
    key: str,
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
):
    """Get a single setting."""
    setting = await SystemSettingsService.get(db, category, key)
    if setting is None:
        raise HTTPException(status_code=404, detail=f"Setting {category}.{key} not found")
    return setting


@router.put("/settings/{category}/{key}", response_model=SystemSettingResponse)
async def update_setting(
    category: str,
    key: str,
    body: SystemSettingUpdate,
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
):
    """Update a single setting."""
    result = await SystemSettingsService.set(
        db,
        category=category,
        key=key,
        value=body.value,
        value_type=body.value_type,
        is_secret=body.is_secret,
        description=body.description,
    )
    await db.flush()
    logger.info("admin_setting_updated", category=category, key=key)
    return result


@router.put("/settings", response_model=list[SystemSettingResponse])
async def bulk_update_settings(
    body: BulkSettingsUpdate,
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
):
    """Bulk update settings within a category."""
    results = await SystemSettingsService.set_bulk(
        db,
        category=body.category,
        settings=[s.model_dump() for s in body.settings],
    )
    await db.flush()
    logger.info(
        "admin_settings_bulk_updated",
        category=body.category,
        count=len(body.settings),
    )
    return results


@router.delete("/settings/{category}/{key}")
async def delete_setting(
    category: str,
    key: str,
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
):
    """Delete a setting."""
    deleted = await SystemSettingsService.delete(db, category, key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Setting {category}.{key} not found")
    await db.flush()
    return {"deleted": True, "category": category, "key": key}


@router.post("/settings/seed")
async def seed_settings(
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
):
    """Re-seed default settings (only creates missing ones)."""
    count = await SystemSettingsService.seed_defaults(db)
    await db.flush()
    return {"seeded": count, "message": f"Created {count} new default settings"}


# ── System Info ──────────────────────────────────────────────────────────


@router.get("/system-info", response_model=SystemInfoResponse)
async def get_system_info(
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
):
    """Get system diagnostics."""
    # Provider counts
    provider_result = await db.execute(select(func.count(Provider.id)))
    provider_count = provider_result.scalar() or 0

    active_result = await db.execute(
        select(func.count(Provider.id)).where(Provider.enabled.is_(True))
    )
    active_providers = active_result.scalar() or 0

    # Profile count
    profile_result = await db.execute(select(func.count(VoiceProfile.id)))
    profile_count = profile_result.scalar() or 0

    # Synthesis count
    synth_result = await db.execute(select(func.count(SynthesisHistory.id)))
    total_synthesis = synth_result.scalar() or 0

    # Redis check
    redis_connected = False
    try:
        import redis as redis_lib

        r = redis_lib.Redis.from_url(app_settings.redis_url, socket_timeout=2)
        r.ping()
        redis_connected = True
    except Exception:
        pass

    # Celery check
    celery_connected = False
    try:
        from app.core.celery_app import celery_app

        insp = celery_app.control.inspect(timeout=2)
        celery_connected = bool(insp.ping())
    except Exception:
        pass

    # Healing status
    healing_enabled = False
    healing_running = False
    try:
        from app.healing.engine import healing_engine

        healing_enabled = healing_engine.enabled
        healing_running = healing_engine._running
    except Exception:
        pass

    return SystemInfoResponse(
        app_name=app_settings.app_name,
        app_env=app_settings.app_env,
        version=app_settings.app_version,
        debug=app_settings.debug,
        uptime_seconds=round(time.monotonic() - _startup_time, 1),
        database_type="PostgreSQL" if not app_settings.is_sqlite else "SQLite",
        provider_count=provider_count,
        active_providers=active_providers,
        profile_count=profile_count,
        total_synthesis=total_synthesis,
        redis_connected=redis_connected,
        celery_connected=celery_connected,
        healing_enabled=healing_enabled,
        healing_running=healing_running,
    )


# ── Backup / Restore ────────────────────────────────────────────────────


@router.post("/backup", response_model=BackupResponse)
async def backup_settings(
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
):
    """Export all settings as an encrypted JSON backup."""
    data = await SystemSettingsService.export_all(db)
    json_str = json.dumps(data, default=str)
    encrypted = encrypt_value(json_str)
    return BackupResponse(
        data=encrypted,
        settings_count=len(data),
        created_at=datetime.now(UTC),
    )


# ── Voice fingerprint duplicates (SC-46) ────────────────────────────────


@router.get("/voice-fingerprints/duplicates")
async def list_fingerprint_duplicates(
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
    threshold: float = Query(
        default=None,
        description="Override the cosine-similarity threshold (default: settings.fingerprint_match_threshold)",
    ),
) -> dict:
    """Return cross-profile fingerprint matches above the threshold.

    Scans every stored fingerprint and pairs it with every fingerprint from
    a *different* profile whose cosine similarity exceeds ``threshold``.
    The result is a list of unique profile-to-profile matches with the
    best-matching similarity score between them.
    """
    import json

    from app.core.config import settings as _settings
    from app.models.voice_fingerprint import VoiceFingerprint
    from app.services.voice_fingerprinter import cosine_similarity

    effective_threshold = (
        threshold if threshold is not None else _settings.fingerprint_match_threshold
    )

    result = await db.execute(select(VoiceFingerprint))
    rows = list(result.scalars().all())

    # Decode once.
    parsed: list[tuple[VoiceFingerprint, list[float]]] = []
    for row in rows:
        try:
            emb = json.loads(row.embedding_json)
        except (ValueError, TypeError):
            continue
        parsed.append((row, emb))

    # Pair-wise compare (O(n^2)) — adequate for an admin diagnostics view.
    best_matches: dict[tuple[str, str], dict] = {}
    for i in range(len(parsed)):
        row_a, emb_a = parsed[i]
        for j in range(i + 1, len(parsed)):
            row_b, emb_b = parsed[j]
            if row_a.profile_id == row_b.profile_id:
                continue
            score = cosine_similarity(emb_a, emb_b)
            if score < effective_threshold:
                continue
            key = tuple(sorted((row_a.profile_id, row_b.profile_id)))
            existing = best_matches.get(key)
            if existing is None or score > existing["similarity"]:
                best_matches[key] = {
                    "profile_a": key[0],
                    "profile_b": key[1],
                    "similarity": round(score, 6),
                    "fingerprint_a_id": row_a.id,
                    "fingerprint_b_id": row_b.id,
                }

    matches = sorted(
        best_matches.values(), key=lambda m: m["similarity"], reverse=True
    )
    return {
        "threshold": effective_threshold,
        "count": len(matches),
        "matches": matches,
    }


@router.post("/restore")
async def restore_settings(
    body: RestoreRequest,
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
):
    """Restore settings from an encrypted backup."""
    try:
        decrypted = decrypt_value(body.data)
        settings_data = json.loads(decrypted)
    except Exception as e:
        logger.error("admin_restore_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted backup data. Ensure the backup was created by this system.",
        )

    count = await SystemSettingsService.import_all(db, settings_data)
    await db.flush()
    logger.info("admin_settings_restored", count=count)
    return {"restored": count, "message": f"Restored {count} settings"}
