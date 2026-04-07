"""Storage cleanup service — purge stale synthesis output and temp files.

Provides a single ``cleanup_old_files`` coroutine that walks the output and
audio-design directories, removes files older than a configurable retention
period, and deletes orphaned SynthesisHistory rows whose files are missing.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Default retention: 7 days for synthesis output, 30 days for audio design
DEFAULT_OUTPUT_RETENTION_DAYS = 7
DEFAULT_DESIGN_RETENTION_DAYS = 30


async def cleanup_old_files(
    db: AsyncSession,
    output_retention_days: int = DEFAULT_OUTPUT_RETENTION_DAYS,
    design_retention_days: int = DEFAULT_DESIGN_RETENTION_DAYS,
    dry_run: bool = False,
) -> dict:
    """Remove stale audio files and orphaned history rows.

    Args:
        db: Async database session.
        output_retention_days: Delete synthesis output files older than this.
        design_retention_days: Delete audio design files older than this.
        dry_run: If True, report what would be deleted without removing anything.

    Returns:
        Summary dict with counts of files and rows removed.
    """
    now = time.time()
    output_cutoff = now - (output_retention_days * 86400)
    design_cutoff = now - (design_retention_days * 86400)

    stats = {
        "output_files_deleted": 0,
        "output_bytes_freed": 0,
        "design_files_deleted": 0,
        "design_bytes_freed": 0,
        "history_rows_cleaned": 0,
        "dry_run": dry_run,
    }

    # 1. Clean synthesis output directory
    output_dir = Path(settings.storage_path) / "output"
    if output_dir.exists():
        for file_path in output_dir.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < output_cutoff:
                size = file_path.stat().st_size
                if not dry_run:
                    file_path.unlink()
                stats["output_files_deleted"] += 1
                stats["output_bytes_freed"] += size

    # 2. Clean preview cache
    preview_dir = Path(settings.storage_path) / "output" / "previews"
    if preview_dir.exists():
        for file_path in preview_dir.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < output_cutoff:
                size = file_path.stat().st_size
                if not dry_run:
                    file_path.unlink()
                stats["output_files_deleted"] += 1
                stats["output_bytes_freed"] += size

    # 3. Clean audio design working directory
    design_dir = Path(settings.storage_path) / "audio-design"
    if design_dir.exists():
        for file_path in design_dir.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < design_cutoff:
                size = file_path.stat().st_size
                if not dry_run:
                    file_path.unlink()
                stats["design_files_deleted"] += 1
                stats["design_bytes_freed"] += size

    # 4. Clean orphaned SynthesisHistory rows (output file no longer exists)
    from app.models.synthesis_history import SynthesisHistory

    cutoff_dt = datetime.now(UTC) - timedelta(days=output_retention_days)
    result = await db.execute(
        select(SynthesisHistory).where(
            SynthesisHistory.created_at < cutoff_dt,
        )
    )
    old_rows = result.scalars().all()
    for row in old_rows:
        if row.output_path and not Path(row.output_path).exists():
            if not dry_run:
                await db.delete(row)
            stats["history_rows_cleaned"] += 1

    if not dry_run:
        await db.flush()

    logger.info(
        "storage_cleanup_completed",
        **stats,
        output_retention_days=output_retention_days,
        design_retention_days=design_retention_days,
    )

    return stats


def get_storage_stats() -> dict:
    """Return current storage usage statistics."""
    storage_path = Path(settings.storage_path)
    dirs = {
        "output": storage_path / "output",
        "samples": storage_path / "samples",
        "audio_design": storage_path / "audio-design",
        "models": storage_path / "models",
    }

    stats = {}
    for name, dir_path in dirs.items():
        if dir_path.exists():
            files = list(dir_path.rglob("*"))
            file_count = sum(1 for f in files if f.is_file())
            total_bytes = sum(f.stat().st_size for f in files if f.is_file())
            stats[name] = {
                "file_count": file_count,
                "total_bytes": total_bytes,
                "total_mb": round(total_bytes / (1024 * 1024), 2),
            }
        else:
            stats[name] = {"file_count": 0, "total_bytes": 0, "total_mb": 0.0}

    return stats
