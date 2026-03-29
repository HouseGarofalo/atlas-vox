"""Health check endpoint."""


from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

logger = structlog.get_logger(__name__)

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/health")
async def health_check(db: DbSession) -> dict:
    """Deep system health check — verifies database and storage dependencies."""
    logger.debug("health_check_called")

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
        import redis

        r = redis.Redis.from_url(settings.redis_url, socket_timeout=3)
        r.ping()
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
        "version": "0.1.0",
    }
