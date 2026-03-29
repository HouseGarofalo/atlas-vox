"""Periodic cleanup task for audio output files."""
from __future__ import annotations

import time
from pathlib import Path

import structlog

from app.core.config import settings
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)

RETENTION_DAYS = 7


@celery_app.task(name="app.tasks.cleanup.cleanup_old_audio")
def cleanup_old_audio(retention_days: int = RETENTION_DAYS) -> dict:
    """Delete audio files in storage/output/ older than retention_days."""
    output_dir = Path(settings.storage_path) / "output"
    if not output_dir.exists():
        return {"deleted": 0, "errors": 0}

    cutoff = time.time() - (retention_days * 86400)
    deleted = 0
    errors = 0

    for f in output_dir.iterdir():
        if not f.is_file():
            continue
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1
                logger.info("cleanup_deleted_file", file=f.name)
        except Exception as e:
            errors += 1
            logger.error("cleanup_error", file=f.name, error=str(e))

    logger.info("cleanup_complete", deleted=deleted, errors=errors)
    return {"deleted": deleted, "errors": errors}
