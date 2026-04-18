"""Celery tasks for audio preprocessing."""

from __future__ import annotations

from pathlib import Path

import structlog

from app.core.config import settings
from app.tasks.celery_app import celery_app
from app.tasks.utils import run_async

logger = structlog.get_logger(__name__)


async def _preprocess_profile_samples(profile_id: str, task) -> dict:
    """Async implementation of sample preprocessing."""
    from sqlalchemy import select

    from app.models.audio_sample import AudioSample
    from app.services.audio_processor import PreprocessConfig, preprocess_audio
    from app.tasks.utils import worker_session

    config = PreprocessConfig()
    processed = 0
    errors = []

    async with worker_session() as db:
        result = await db.execute(
            select(AudioSample).where(
                AudioSample.profile_id == profile_id,
                AudioSample.preprocessed == False,  # noqa: E712
            )
        )
        samples = result.scalars().all()
        total = len(samples)

        if total == 0:
            return {"processed": 0, "errors": [], "total": 0}

        for i, sample in enumerate(samples):
            try:
                input_path = Path(sample.file_path)
                output_dir = Path(settings.storage_path) / "preprocessed" / profile_id
                output_path = output_dir / f"{input_path.stem}_pp.wav"

                await preprocess_audio(input_path, output_path, config)

                sample.preprocessed = True
                sample.preprocessed_path = str(output_path)
                processed += 1

                # Update Celery task progress
                task.update_state(
                    state="PROGRESS",
                    meta={
                        "current": i + 1,
                        "total": total,
                        "percent": round((i + 1) / total * 100, 1),
                        "status": f"Preprocessed {i + 1}/{total}",
                    },
                )
            except Exception as e:
                logger.error("preprocessing_failed", sample_id=sample.id, error=str(e))
                errors.append({"sample_id": sample.id, "error": str(e)})

        await db.commit()

    return {"processed": processed, "errors": errors, "total": total}


@celery_app.task(bind=True, name="app.tasks.preprocessing.preprocess_samples")
def preprocess_samples(self, profile_id: str) -> dict:
    """Preprocess all unprocessed samples for a profile."""
    logger.info("preprocessing_started", profile_id=profile_id, task_id=self.request.id)

    self.update_state(state="PROGRESS", meta={"current": 0, "total": 0, "percent": 0, "status": "Starting..."})

    result = run_async(_preprocess_profile_samples(profile_id, self))

    logger.info(
        "preprocessing_complete",
        profile_id=profile_id,
        processed=result["processed"],
        errors=len(result["errors"]),
    )
    return result


# ---------------------------------------------------------------------------
# Voice fingerprinting (SC-46)
# ---------------------------------------------------------------------------


async def _compute_sample_fingerprint(sample_id: str) -> dict:
    """Compute and persist a voice fingerprint for a single uploaded sample.

    Called in the background after sample upload so the main request
    doesn't have to wait for the embedding to finish.
    """
    from sqlalchemy import select

    from app.models.audio_sample import AudioSample
    from app.models.voice_fingerprint import VoiceFingerprint
    from app.services.voice_fingerprinter import (
        compute_fingerprint_with_method,
        store_fingerprint,
    )
    from app.tasks.utils import worker_session

    async with worker_session() as db:
        result = await db.execute(
            select(AudioSample).where(AudioSample.id == sample_id)
        )
        sample = result.scalar_one_or_none()
        if sample is None:
            logger.warning("fingerprint_sample_not_found", sample_id=sample_id)
            return {"sample_id": sample_id, "ok": False, "reason": "not_found"}

        # Skip if a fingerprint already exists.
        existing = await db.execute(
            select(VoiceFingerprint).where(VoiceFingerprint.sample_id == sample_id)
        )
        if existing.scalar_one_or_none() is not None:
            return {"sample_id": sample_id, "ok": True, "reason": "already_exists"}

        try:
            embedding, method = await compute_fingerprint_with_method(
                Path(sample.file_path)
            )
        except Exception as exc:
            logger.warning(
                "fingerprint_compute_failed",
                sample_id=sample_id,
                error=str(exc),
            )
            return {"sample_id": sample_id, "ok": False, "reason": str(exc)}

        await store_fingerprint(
            db,
            sample_id=sample.id,
            profile_id=sample.profile_id,
            embedding=embedding,
            method=method,
        )
        await db.commit()

    return {"sample_id": sample_id, "ok": True, "dims": len(embedding), "method": method}


@celery_app.task(bind=True, name="app.tasks.preprocessing.compute_sample_fingerprint")
def compute_sample_fingerprint(self, sample_id: str) -> dict:
    """Celery entry point for background fingerprint computation."""
    logger.info(
        "fingerprint_task_started",
        sample_id=sample_id,
        task_id=self.request.id,
    )
    result = run_async(_compute_sample_fingerprint(sample_id))
    logger.info("fingerprint_task_complete", sample_id=sample_id, **result)
    return result
