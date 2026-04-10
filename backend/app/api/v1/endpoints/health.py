"""Health check and storage management endpoints."""


from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, Query
from sqlalchemy import text

from app.core.config import settings
from app.core.dependencies import CurrentUser, DbSession, require_scope

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check(db: DbSession) -> dict:
    """Basic system health check — returns only status for unauthenticated access."""
    logger.debug("health_check_called")

    try:
        # Quick database check only
        await db.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as exc:
        logger.error("health_check_db_failed", error=str(exc))
        return {"status": "degraded"}


@router.get("/health/details")
async def health_check_details(db: DbSession, user: CurrentUser) -> dict:
    """Deep system health check with full details — requires authentication."""
    logger.debug("health_check_details_called")

    checks: dict[str, str] = {}
    overall_healthy = True

    # --- Database check ---
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.error("health_check_db_failed", error=str(exc))
        checks["database"] = "error"
        overall_healthy = False

    # --- Redis check ---
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, socket_timeout=3)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        logger.error("health_check_redis_failed", error=str(exc))
        checks["redis"] = "error"
        overall_healthy = False

    # --- Storage check ---
    try:
        storage_dir = Path(settings.storage_path)
        storage_dir.mkdir(parents=True, exist_ok=True)
        probe = storage_dir / ".health_probe"
        probe.write_text("ok")
        probe.unlink()
        checks["storage"] = "ok"
    except Exception as exc:
        logger.error("health_check_storage_failed", error=str(exc))
        checks["storage"] = "error"
        overall_healthy = False

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "checks": checks,
        "version": settings.app_version,
    }


@router.get("/storage/stats")
async def storage_stats(user: Annotated[dict, require_scope("admin")]) -> dict:
    """Return current storage usage statistics (admin only)."""
    from app.services.storage_cleanup import get_storage_stats
    return get_storage_stats()


@router.post("/storage/cleanup")
async def storage_cleanup(
    db: DbSession,
    user: Annotated[dict, require_scope("admin")],
    output_days: int = Query(default=7, ge=1, le=365, description="Delete output files older than N days"),
    design_days: int = Query(default=30, ge=1, le=365, description="Delete design files older than N days"),
    dry_run: bool = Query(default=True, description="Preview what would be deleted without removing"),
) -> dict:
    """Clean up old synthesis output and audio design files (admin only).

    Pass ``dry_run=false`` to actually delete files.
    """
    from app.services.storage_cleanup import cleanup_old_files
    return await cleanup_old_files(
        db,
        output_retention_days=output_days,
        design_retention_days=design_days,
        dry_run=dry_run,
    )
