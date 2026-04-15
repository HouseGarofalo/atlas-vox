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
