"""Celery tasks for model training."""

from __future__ import annotations

import json
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path

import structlog

from app.core.enums import JobStatus, ProfileStatus
from app.tasks.celery_app import celery_app
from app.tasks.utils import run_async

logger = structlog.get_logger(__name__)

# Thread lock for provider registry access in Celery worker processes.
# asyncio.Lock() is meaningless here because Celery tasks run in separate
# processes/threads, not in an asyncio event loop.
_registry_lock = threading.Lock()


def _ensure_wav(file_path: Path) -> Path:
    """Convert to WAV if not already WAV. Returns path to WAV file.

    Uses ffmpeg for conversion to 16kHz mono PCM. This ensures local
    providers like Coqui XTTS can read the audio. Cloud providers
    (ElevenLabs) accept M4A directly so this is only called for
    providers that require WAV.
    """
    if file_path.suffix.lower() == ".wav":
        return file_path
    wav_path = file_path.with_suffix(".wav")
    if wav_path.exists():
        return wav_path
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(file_path),
                "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le",
                str(wav_path),
            ],
            capture_output=True,
            check=True,
        )
        logger.info("converted_to_wav", source=str(file_path), target=str(wav_path))
    except FileNotFoundError:
        logger.warning("ffmpeg_not_found", hint="Install ffmpeg for automatic audio conversion")
        return file_path  # Fall back to original if ffmpeg unavailable
    except subprocess.CalledProcessError as exc:
        logger.warning("ffmpeg_conversion_failed", source=str(file_path), error=exc.stderr.decode(errors="replace"))
        return file_path  # Fall back to original
    return wav_path


async def _load_job_and_samples(db, job_id: str, task):
    """Load the training job from DB, mark it as training, and return job + provider samples."""
    from sqlalchemy import select

    from app.models.audio_sample import AudioSample
    from app.models.training_job import TrainingJob
    from app.providers.base import ProviderAudioSample
    from app.services.provider_registry import provider_registry

    result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        return None, None, None, None

    job.status = JobStatus.TRAINING
    job.started_at = datetime.now(UTC)
    await db.commit()

    task.update_state(state="PROGRESS", meta={
        "percent": 10, "status": "Loading provider...", "job_id": job_id,
    })

    # Load provider config from DB (worker doesn't run lifespan)
    from app.core.encryption import ENC_PREFIX, decrypt_value
    from app.models.provider import Provider as ProviderModel
    prov_result = await db.execute(
        select(ProviderModel).where(ProviderModel.name == job.provider_name)
    )
    prov_row = prov_result.scalar_one_or_none()

    with _registry_lock:
        if prov_row and prov_row.config_json:
            config = json.loads(prov_row.config_json)
            # Decrypt encrypted values (same logic as provider_registry startup)
            failed_fields = []
            for key, val in list(config.items()):
                if isinstance(val, str) and val.startswith(ENC_PREFIX):
                    try:
                        config[key] = decrypt_value(val)
                    except Exception:
                        logger.error("worker_config_decrypt_failed",
                                     provider=job.provider_name, field=key)
                        # Remove field — don't pass encrypted ciphertext to provider
                        del config[key]
                        failed_fields.append(key)
            if failed_fields:
                logger.warning("worker_config_fields_skipped",
                               provider=job.provider_name, fields=failed_fields)
            provider_registry.apply_config(job.provider_name, config)

        provider = provider_registry.get_provider(job.provider_name)
    capabilities = await provider.get_capabilities()

    sample_result = await db.execute(
        select(AudioSample).where(AudioSample.profile_id == job.profile_id)
    )
    samples = sample_result.scalars().all()
    provider_samples = []
    for s in samples:
        path = Path(s.preprocessed_path) if s.preprocessed_path else Path(s.file_path)
        provider_samples.append(ProviderAudioSample(
            file_path=path,
            duration_seconds=s.duration_seconds,
            sample_rate=s.sample_rate,
            transcript=getattr(s, "transcript", None),
        ))

    if not provider_samples:
        raise ValueError("No audio samples available for training")

    # Convert non-WAV files for local providers that only accept WAV input.
    if len(capabilities.supported_output_formats) == 1 and capabilities.supported_output_formats[0] == "wav":
        for i, ps in enumerate(provider_samples):
            wav_path = _ensure_wav(ps.file_path)
            if wav_path != ps.file_path:
                provider_samples[i] = ProviderAudioSample(
                    file_path=wav_path,
                    duration_seconds=ps.duration_seconds,
                    sample_rate=16000,
                )

    return job, provider, capabilities, provider_samples


async def _dispatch_to_provider(provider, capabilities, provider_samples, job, task, job_id: str):
    """Dispatch training to clone_voice or fine_tune based on capabilities."""
    from app.providers.base import CloneConfig, FineTuneConfig

    task.update_state(state="PROGRESS", meta={
        "percent": 25, "status": "Training started...", "job_id": job_id,
    })

    # Pre-check: warn if Azure token is near expiry (training can take hours)
    if job.provider_name == "azure_speech":
        try:
            from app.providers.azure_auth import get_azure_auth_manager
            auth_mgr = get_azure_auth_manager()
            status = auth_mgr.get_status()
            if status.authenticated and status.expires_in_seconds is not None:
                if status.expires_in_seconds < 600:
                    logger.warning(
                        "azure_token_near_expiry_at_training_start",
                        job_id=job_id,
                        expires_in_seconds=status.expires_in_seconds,
                    )
            elif not status.authenticated:
                logger.warning(
                    "azure_not_authenticated_at_training_start",
                    job_id=job_id,
                    hint="Training may fail if no service principal is configured",
                )
        except Exception as exc:
            logger.debug("azure_auth_check_skipped", error=str(exc))

    config_data = json.loads(job.config_json) if job.config_json else {}

    if capabilities.supports_cloning and not config_data.get("fine_tune_model_id"):
        clone_config = CloneConfig(
            name=config_data.get("name", ""),
            description=config_data.get("description", ""),
            language=config_data.get("language", "en"),
        )
        return await provider.clone_voice(provider_samples, clone_config)
    elif capabilities.supports_fine_tuning:
        ft_config = FineTuneConfig(
            epochs=config_data.get("epochs", 10),
            learning_rate=config_data.get("learning_rate", 1e-5),
            batch_size=config_data.get("batch_size", 4),
        )
        model_id = config_data.get("fine_tune_model_id", "default")
        return await provider.fine_tune(model_id, provider_samples, ft_config)
    else:
        raise ValueError(f"Provider '{job.provider_name}' does not support training")


async def _score_version_quality(
    db,
    job,
    version,
    provider,
    provider_samples,
) -> None:
    """Synthesise a test sentence and compute voice quality metrics.

    Updates ``version.metrics_json`` in-place (caller must commit).
    Failures are non-fatal — logged as warnings so training still succeeds.
    """
    from app.services.audio_quality import score_voice_quality

    TEST_SENTENCE = (
        "The quick brown fox jumps over the lazy dog. "
        "She sells sea shells by the sea shore."
    )
    try:
        from app.providers.base import SynthesisSettings

        settings_obj = SynthesisSettings(output_format="wav")
        # Use the trained voice for the test — provider_model_id from the version
        voice_id = version.provider_model_id or "default"
        audio_result = await provider.synthesize(TEST_SENTENCE, voice_id, settings_obj)
        synthesized_path = audio_result.audio_path

        original_paths = [s.file_path for s in provider_samples]
        voice_score = await score_voice_quality(
            original_samples=original_paths,
            synthesized_audio=synthesized_path,
            reference_text=TEST_SENTENCE,
        )

        # Merge quality score into existing metrics_json
        existing: dict = {}
        if version.metrics_json:
            try:
                existing = json.loads(version.metrics_json)
            except json.JSONDecodeError:
                existing = {}
        existing["voice_quality"] = voice_score.to_dict()
        version.metrics_json = json.dumps(existing)

        logger.info(
            "voice_quality_scored",
            job_id=job.id,
            version_id=version.id,
            overall=voice_score.overall,
        )

        # Clean up synthesized test file
        try:
            synthesized_path.unlink(missing_ok=True)
        except Exception:
            pass

    except Exception as exc:
        logger.warning(
            "voice_quality_scoring_failed",
            job_id=job.id,
            version_id=version.id,
            error=str(exc),
        )


async def _create_version(db, job, voice_model, task, job_id: str) -> tuple:
    """Create a ModelVersion record and activate it on the profile."""
    from sqlalchemy import func, select

    from app.models.model_version import ModelVersion
    from app.models.voice_profile import VoiceProfile

    task.update_state(state="PROGRESS", meta={
        "percent": 90, "status": "Creating model version...", "job_id": job_id,
    })

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

    job.status = JobStatus.COMPLETED
    job.progress = 1.0
    job.result_version_id = version.id
    job.completed_at = datetime.now(UTC)

    profile_result = await db.execute(
        select(VoiceProfile).where(VoiceProfile.id == job.profile_id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile:
        profile.active_version_id = version.id
        profile.status = ProfileStatus.READY

    await db.commit()
    return version, next_version


async def _execute_training(job_id: str, task) -> dict:
    """Async training execution — dispatches to the correct provider.

    Uses ``worker_session()`` to create a fresh SQLAlchemy async engine
    scoped to the current event loop.  The module-level engine from
    ``database.py`` is bound to the loop that existed at import time,
    which differs from the loop created by ``asyncio.run()`` in the
    Celery task — reusing it causes:
        RuntimeError: Task got Future attached to a different loop
    """
    from app.tasks.utils import worker_session

    async with worker_session() as db:
        job, provider, capabilities, provider_samples = await _load_job_and_samples(db, job_id, task)
        if job is None:
            return {"error": "Job not found"}

        try:
            voice_model = await _dispatch_to_provider(
                provider, capabilities, provider_samples, job, task, job_id
            )
            version, next_version = await _create_version(db, job, voice_model, task, job_id)

            # Score voice quality post-training (non-fatal if it fails)
            task.update_state(state="PROGRESS", meta={
                "percent": 95, "status": "Scoring voice quality...", "job_id": job_id,
            })
            await _score_version_quality(db, job, version, provider, provider_samples)
            await db.commit()

            logger.info("training_complete", job_id=job_id, version_id=version.id)
            return {
                "job_id": job_id,
                "status": JobStatus.COMPLETED,
                "version_id": version.id,
                "version_number": next_version,
            }

        except Exception as e:
            job.status = JobStatus.FAILED
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

    result = run_async(_execute_training(job_id, self))
    return result
