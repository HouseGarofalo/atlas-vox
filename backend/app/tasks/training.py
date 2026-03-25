"""Celery tasks for model training."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


def _run_async(coro):
    """Run an async coroutine from sync Celery task context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        pass
    return asyncio.run(coro)


async def _execute_training(job_id: str, task) -> dict:
    """Async training execution — dispatches to the correct provider."""
    from sqlalchemy import func, select

    from app.core.database import async_session_factory
    from app.models.audio_sample import AudioSample
    from app.models.model_version import ModelVersion
    from app.models.training_job import TrainingJob
    from app.models.voice_profile import VoiceProfile
    from app.providers.base import AudioSample as ProviderSample
    from app.providers.base import CloneConfig, FineTuneConfig
    from app.services.provider_registry import provider_registry

    async with async_session_factory() as db:
        # Load job
        result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            return {"error": "Job not found"}

        try:
            # Mark as training
            job.status = "training"
            job.started_at = datetime.now(UTC)
            await db.commit()

            task.update_state(state="PROGRESS", meta={
                "percent": 10, "status": "Loading provider...", "job_id": job_id,
            })

            # Get provider
            provider = provider_registry.get_provider(job.provider_name)
            capabilities = await provider.get_capabilities()

            # Load preprocessed samples (prefer preprocessed, fall back to original)
            result = await db.execute(
                select(AudioSample).where(AudioSample.profile_id == job.profile_id)
            )
            samples = result.scalars().all()
            provider_samples = []
            for s in samples:
                path = Path(s.preprocessed_path) if s.preprocessed_path else Path(s.file_path)
                provider_samples.append(ProviderSample(
                    file_path=path,
                    duration_seconds=s.duration_seconds,
                    sample_rate=s.sample_rate,
                ))

            if not provider_samples:
                raise ValueError("No audio samples available for training")

            task.update_state(state="PROGRESS", meta={
                "percent": 25, "status": "Training started...", "job_id": job_id,
            })

            # Parse training config
            config_data = json.loads(job.config_json) if job.config_json else {}

            # Dispatch to provider: clone_voice or fine_tune
            if capabilities.supports_cloning and not config_data.get("fine_tune_model_id"):
                clone_config = CloneConfig(
                    name=config_data.get("name", ""),
                    description=config_data.get("description", ""),
                    language=config_data.get("language", "en"),
                )
                voice_model = await provider.clone_voice(provider_samples, clone_config)
            elif capabilities.supports_fine_tuning:
                ft_config = FineTuneConfig(
                    epochs=config_data.get("epochs", 10),
                    learning_rate=config_data.get("learning_rate", 1e-5),
                    batch_size=config_data.get("batch_size", 4),
                )
                model_id = config_data.get("fine_tune_model_id", "default")
                voice_model = await provider.fine_tune(model_id, provider_samples, ft_config)
            else:
                raise ValueError(f"Provider '{job.provider_name}' does not support training")

            task.update_state(state="PROGRESS", meta={
                "percent": 90, "status": "Creating model version...", "job_id": job_id,
            })

            # Create model version
            version_count = await db.execute(
                select(func.count()).where(ModelVersion.profile_id == job.profile_id)
            )
            next_version = (version_count.scalar() or 0) + 1

            version = ModelVersion(
                profile_id=job.profile_id,
                version_number=next_version,
                provider_model_id=voice_model.provider_model_id,
                model_path=str(voice_model.model_path) if voice_model.model_path else None,
                config_json=job.config_json,
                metrics_json=json.dumps(voice_model.metrics) if voice_model.metrics else None,
            )
            db.add(version)
            await db.flush()

            # Update job as completed
            job.status = "completed"
            job.progress = 1.0
            job.result_version_id = version.id
            job.completed_at = datetime.now(UTC)

            # Activate version on the profile
            result = await db.execute(
                select(VoiceProfile).where(VoiceProfile.id == job.profile_id)
            )
            profile = result.scalar_one_or_none()
            if profile:
                profile.active_version_id = version.id
                profile.status = "ready"

            await db.commit()

            logger.info("training_complete", job_id=job_id, version_id=version.id)
            return {
                "job_id": job_id,
                "status": "completed",
                "version_id": version.id,
                "version_number": next_version,
            }

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(UTC)
            await db.commit()

            logger.error("training_failed", job_id=job_id, error=str(e))
            raise  # Re-raise so Celery records as FAILURE


@celery_app.task(bind=True, name="app.tasks.training.train_model")
def train_model(self, job_id: str) -> dict:
    """Execute a training job — dispatches to the correct provider."""
    logger.info("training_task_started", job_id=job_id, task_id=self.request.id)

    self.update_state(state="PROGRESS", meta={
        "percent": 0, "status": "Initializing...", "job_id": job_id,
    })

    result = _run_async(_execute_training(job_id, self))
    return result
