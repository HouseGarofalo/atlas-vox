"""Audio sample endpoints — upload, list, delete, analysis, preprocessing."""


import asyncio
import json
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import CurrentUser, DbSession
from app.core.rate_limit import limiter
from app.models.audio_sample import AudioSample
from app.models.voice_profile import VoiceProfile
from app.schemas.quality import AudioQualityReportSchema, TrainingReadinessSchema
from app.schemas.sample import (
    PronunciationAssessment,
    SampleAnalysis,
    SampleListResponse,
    SampleResponse,
    TranscribeRequest,
    TranscribeResponse,
)
from app.services.audio_processor import analyze_audio
from app.services.audio_quality import assess_training_readiness, validate_audio_quality

logger = structlog.get_logger(__name__)

ALLOWED_FORMATS = {"wav", "mp3", "flac", "ogg", "m4a", "webm"}
# Formats that need conversion to WAV before storage/processing
_CONVERT_TO_WAV = {"webm"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB per file
MAX_FILES_PER_UPLOAD = 20
# Aggregate cap guards against 20 × 50MB = 1GB per request. Tightened to 500MB
# total so one upload can't overwhelm the storage volume or memory buffer.
MAX_TOTAL_UPLOAD_BYTES = 500 * 1024 * 1024

router = APIRouter(prefix="/profiles/{profile_id}/samples", tags=["samples"])


async def _convert_to_wav(src: Path) -> Path:
    """Convert an audio file to WAV using ffmpeg. Returns the new path."""
    dst = src.with_suffix(".wav")
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(src),
        "-ar", "22050", "-ac", "1", "-sample_fmt", "s16",
        str(dst),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {stderr.decode(errors='replace')[:500]}")
    # Remove original
    src.unlink(missing_ok=True)
    return dst


async def _get_profile_or_404(db: DbSession, profile_id: str) -> VoiceProfile:
    result = await db.execute(
        select(VoiceProfile).where(VoiceProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


async def _get_sample_or_404(db: DbSession, profile_id: str, sample_id: str) -> AudioSample:
    result = await db.execute(
        select(AudioSample).where(
            AudioSample.id == sample_id,
            AudioSample.profile_id == profile_id,
        )
    )
    sample = result.scalar_one_or_none()
    if sample is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")
    return sample


@router.post("", response_model=list[SampleResponse], status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def upload_samples(
    request: Request,
    profile_id: str,
    db: DbSession,
    user: CurrentUser,
    files: list[UploadFile] = File(...),
) -> list[SampleResponse]:
    """Upload one or more audio sample files."""
    await _get_profile_or_404(db, profile_id)

    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_FILES_PER_UPLOAD} files per upload",
        )

    storage_dir = Path(settings.storage_path) / "samples" / profile_id
    storage_dir.mkdir(parents=True, exist_ok=True)

    created: list[SampleResponse] = []
    total_bytes = 0  # aggregate size enforced across the whole request
    for upload in files:
        if not upload.filename:
            continue
        ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else ""
        if ext not in ALLOWED_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_FORMATS))}",
            )

        file_id = uuid.uuid4().hex[:12]
        stored_name = f"{file_id}.{ext}"
        file_path = storage_dir / stored_name

        content = await upload.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{upload.filename}' exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit",
            )
        total_bytes += len(content)
        if total_bytes > MAX_TOTAL_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"Upload exceeds aggregate limit of "
                    f"{MAX_TOTAL_UPLOAD_BYTES // (1024 * 1024)}MB per request"
                ),
            )
        file_path.write_bytes(content)

        # Convert browser-recorded formats (webm) to WAV for provider compatibility
        if ext in _CONVERT_TO_WAV:
            try:
                file_path = await _convert_to_wav(file_path)
                ext = "wav"
                stored_name = file_path.name
                logger.info("webm_converted_to_wav", original=upload.filename, stored=stored_name)
            except Exception as conv_err:
                file_path.unlink(missing_ok=True)
                logger.error("audio_conversion_failed", filename=upload.filename, error=str(conv_err))
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Failed to convert '{upload.filename}' to WAV: {conv_err}",
                )

        sample = AudioSample(
            profile_id=profile_id,
            filename=stored_name,
            original_filename=upload.filename,
            file_path=str(file_path),
            format=ext,
            file_size_bytes=file_path.stat().st_size,
        )
        db.add(sample)
        await db.flush()

        # Auto-analyze to populate duration_seconds and sample_rate
        try:
            analysis = await analyze_audio(file_path)
            sample.duration_seconds = analysis.duration_seconds
            sample.sample_rate = analysis.sample_rate
            sample.analysis_json = json.dumps({
                "duration_seconds": analysis.duration_seconds,
                "sample_rate": analysis.sample_rate,
                "pitch_mean": analysis.pitch_mean,
                "pitch_std": analysis.pitch_std,
                "energy_mean": analysis.energy_mean,
                "energy_std": analysis.energy_std,
            })
            await db.flush()
        except Exception as exc:
            logger.warning("auto_analysis_failed", sample_id=sample.id, error=str(exc))

        # Fire-and-forget voice fingerprint computation (SC-46). Best-effort:
        # if Celery is unavailable (e.g. in tests without a broker) we fall
        # back to an inline async task so the fingerprint still gets stored.
        try:
            from app.tasks.preprocessing import compute_sample_fingerprint

            compute_sample_fingerprint.delay(sample.id)
            logger.info("fingerprint_dispatched", sample_id=sample.id)
        except Exception as fp_exc:
            logger.warning(
                "fingerprint_celery_dispatch_failed",
                sample_id=sample.id,
                error=str(fp_exc),
            )
            try:
                from app.services.voice_fingerprinter import (
                    compute_fingerprint_with_method,
                    store_fingerprint,
                )

                embedding, method = await compute_fingerprint_with_method(file_path)
                await store_fingerprint(
                    db,
                    sample_id=sample.id,
                    profile_id=profile_id,
                    embedding=embedding,
                    method=method,
                )
            except Exception as inline_exc:
                logger.warning(
                    "fingerprint_inline_failed",
                    sample_id=sample.id,
                    error=str(inline_exc),
                )

        logger.info("sample_uploaded", sample_id=sample.id, profile_id=profile_id, filename=upload.filename)
        created.append(SampleResponse.model_validate(sample))

    return created


@router.get("", response_model=SampleListResponse)
async def list_samples(
    profile_id: str,
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
) -> SampleListResponse:
    """List all audio samples for a profile."""
    logger.info("list_samples_called", profile_id=profile_id, limit=limit, offset=offset)
    await _get_profile_or_404(db, profile_id)
    result = await db.execute(
        select(AudioSample)
        .where(AudioSample.profile_id == profile_id)
        .order_by(AudioSample.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    samples = result.scalars().all()
    logger.info("list_samples_returned", profile_id=profile_id, count=len(samples))
    return SampleListResponse(
        samples=[SampleResponse.model_validate(s) for s in samples],
        count=len(samples),
    )


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample(
    profile_id: str, sample_id: str, db: DbSession, user: CurrentUser
):
    """Delete a sample and its file."""
    sample = await _get_sample_or_404(db, profile_id, sample_id)

    # Remove file from disk
    file_path = Path(sample.file_path)
    if file_path.exists():
        file_path.unlink()
    if sample.preprocessed_path:
        pp = Path(sample.preprocessed_path)
        if pp.exists():
            pp.unlink()

    await db.delete(sample)
    await db.flush()
    logger.info("sample_deleted", sample_id=sample_id, profile_id=profile_id)


@router.get("/{sample_id}/analysis", response_model=SampleAnalysis)
async def get_sample_analysis(
    profile_id: str, sample_id: str, db: DbSession, user: CurrentUser
) -> SampleAnalysis:
    """Return audio analysis (pitch, energy, duration) for a sample.

    Runs analysis on demand and caches in the DB.
    """
    logger.info("get_sample_analysis_called", profile_id=profile_id, sample_id=sample_id)
    sample = await _get_sample_or_404(db, profile_id, sample_id)

    # Use cached analysis if available
    cached = bool(sample.analysis_json)
    logger.info("get_sample_analysis_cache", profile_id=profile_id, sample_id=sample_id, cached=cached)
    if sample.analysis_json:
        data = json.loads(sample.analysis_json)
        return SampleAnalysis(
            sample_id=sample.id,
            duration_seconds=data.get("duration_seconds", 0),
            sample_rate=data.get("sample_rate", 0),
            pitch_mean=data.get("pitch_mean"),
            pitch_std=data.get("pitch_std"),
            energy_mean=data.get("energy_mean"),
            energy_std=data.get("energy_std"),
        )

    # Run analysis
    analysis = await analyze_audio(Path(sample.file_path))

    # Cache in DB
    sample.analysis_json = analysis.to_json()
    sample.duration_seconds = analysis.duration_seconds
    sample.sample_rate = analysis.sample_rate
    await db.flush()

    return SampleAnalysis(
        sample_id=sample.id,
        duration_seconds=analysis.duration_seconds,
        sample_rate=analysis.sample_rate,
        pitch_mean=analysis.pitch_mean,
        pitch_std=analysis.pitch_std,
        energy_mean=analysis.energy_mean,
        energy_std=analysis.energy_std,
    )


@router.post("/preprocess", status_code=status.HTTP_202_ACCEPTED)
async def trigger_preprocessing(
    profile_id: str, db: DbSession, user: CurrentUser
) -> dict:
    """Trigger async preprocessing of all unprocessed samples for a profile.

    Queues a Celery task and returns the task ID.
    """
    logger.info("trigger_preprocessing_called", profile_id=profile_id)
    await _get_profile_or_404(db, profile_id)

    result = await db.execute(
        select(AudioSample).where(
            AudioSample.profile_id == profile_id,
            AudioSample.preprocessed == False,  # noqa: E712
        )
    )
    unprocessed = result.scalars().all()
    if not unprocessed:
        return {"message": "All samples already preprocessed", "task_id": None}

    from app.tasks.preprocessing import preprocess_samples

    task = preprocess_samples.delay(profile_id)
    logger.info("preprocessing_queued", profile_id=profile_id, task_id=task.id, count=len(unprocessed))

    return {"message": f"Preprocessing queued for {len(unprocessed)} samples", "task_id": task.id}


@router.post("/{sample_id}/transcribe", response_model=TranscribeResponse)
async def transcribe_sample(
    profile_id: str, sample_id: str,
    data: TranscribeRequest,
    db: DbSession, user: CurrentUser,
) -> TranscribeResponse:
    """Transcribe a sample using the profile's provider STT (Azure Speech-to-Text)."""
    profile = await _get_profile_or_404(db, profile_id)
    sample = await _get_sample_or_404(db, profile_id, sample_id)

    from app.services.provider_registry import provider_registry

    provider = provider_registry.get_provider(profile.provider_name)
    caps = await provider.get_capabilities()
    if not caps.supports_transcription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{profile.provider_name}' does not support transcription",
        )

    try:
        transcript = await provider.transcribe(Path(sample.file_path), locale=data.locale)
    except Exception as e:
        logger.error("transcription_failed", sample_id=sample_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Transcription failed. Check server logs.")

    sample.transcript = transcript
    sample.transcript_source = "azure_stt"
    await db.flush()

    logger.info("sample_transcribed", sample_id=sample_id, length=len(transcript))
    return TranscribeResponse(sample_id=sample.id, transcript=transcript)


@router.post("/{sample_id}/assess", response_model=PronunciationAssessment)
async def assess_sample(
    profile_id: str, sample_id: str,
    db: DbSession, user: CurrentUser,
    reference_text: str | None = Query(None, description="Reference text for assessment. Uses stored transcript if omitted."),
    locale: str = Query("en-US"),
) -> PronunciationAssessment:
    """Assess pronunciation quality of a sample using Azure Pronunciation Assessment."""
    profile = await _get_profile_or_404(db, profile_id)
    sample = await _get_sample_or_404(db, profile_id, sample_id)

    from app.services.provider_registry import provider_registry

    provider = provider_registry.get_provider(profile.provider_name)
    caps = await provider.get_capabilities()
    if not caps.supports_pronunciation_assessment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{profile.provider_name}' does not support pronunciation assessment",
        )

    ref_text = reference_text or sample.transcript
    if not ref_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reference text required — provide it or transcribe the sample first",
        )

    try:
        score = await provider.assess_pronunciation(Path(sample.file_path), ref_text, locale=locale)
    except Exception as e:
        logger.error("pronunciation_assessment_failed", sample_id=sample_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Pronunciation assessment failed. Check server logs.")

    import json as _json
    sample.pronunciation_json = _json.dumps({
        "accuracy_score": score.accuracy_score,
        "fluency_score": score.fluency_score,
        "completeness_score": score.completeness_score,
        "pronunciation_score": score.pronunciation_score,
    })
    await db.flush()

    logger.info("sample_assessed", sample_id=sample_id, accuracy=score.accuracy_score)
    return PronunciationAssessment(
        sample_id=sample.id,
        accuracy_score=score.accuracy_score,
        fluency_score=score.fluency_score,
        completeness_score=score.completeness_score,
        pronunciation_score=score.pronunciation_score,
        word_scores=score.word_scores,
    )


@router.get("/{sample_id}/quality", response_model=AudioQualityReportSchema)
async def get_sample_quality(
    profile_id: str,
    sample_id: str,
    db: DbSession,
    user: CurrentUser,
    force: bool = Query(default=False, description="Re-run quality analysis even if cached"),
) -> AudioQualityReportSchema:
    """Get or compute audio quality report for a sample.

    Results are cached in ``sample.analysis_json`` under the ``quality``
    key.  Pass ``?force=true`` to recompute from scratch.
    """
    sample = await _get_sample_or_404(db, profile_id, sample_id)

    # ── Return cached result when available and not forcing refresh ───────────
    if not force and sample.analysis_json:
        cached = json.loads(sample.analysis_json)
        if "quality" in cached:
            q = cached["quality"]
            logger.info(
                "sample_quality_cache_hit",
                sample_id=sample_id,
                score=q.get("score"),
            )
            return AudioQualityReportSchema(**q)

    # ── Run validation ────────────────────────────────────────────────────────
    logger.info("sample_quality_compute_start", sample_id=sample_id, profile_id=profile_id)
    try:
        report = await validate_audio_quality(Path(sample.file_path))
    except Exception as exc:
        logger.error("sample_quality_failed", sample_id=sample_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Quality analysis failed: {exc}",
        ) from exc

    # ── Persist into analysis_json alongside any existing analysis data ───────
    existing: dict = {}
    if sample.analysis_json:
        try:
            existing = json.loads(sample.analysis_json)
        except json.JSONDecodeError:
            existing = {}
    existing["quality"] = report.to_dict()
    sample.analysis_json = json.dumps(existing)
    await db.flush()

    logger.info(
        "sample_quality_computed",
        sample_id=sample_id,
        score=report.score,
        passed=report.passed,
    )
    return AudioQualityReportSchema(**report.to_dict())


@router.get("/readiness", response_model=TrainingReadinessSchema)
async def get_training_readiness(
    profile_id: str,
    db: DbSession,
    user: CurrentUser,
) -> TrainingReadinessSchema:
    """Assess whether the profile's samples are ready for training.

    Loads all samples for the profile, runs quality validation for any sample
    that has not yet been evaluated, and returns a readiness report with a
    0-100 score and actionable recommendations.
    """
    profile = await _get_profile_or_404(db, profile_id)

    result = await db.execute(
        select(AudioSample)
        .where(AudioSample.profile_id == profile_id)
        .order_by(AudioSample.created_at.asc())
    )
    samples = result.scalars().all()

    if not samples:
        return TrainingReadinessSchema(
            ready=False,
            score=0.0,
            sample_count=0,
            total_duration=0.0,
            issues=[
                {
                    "code": "no_samples",
                    "severity": "error",
                    "message": "No audio samples found for this profile",
                    "value": None,
                    "threshold": None,
                }
            ],
            recommendations=["Upload at least 2 audio samples to begin training."],
        )

    # Build the list expected by assess_training_readiness, using cached quality
    # reports where available to avoid redundant computation.
    sample_dicts: list[dict] = []
    for s in samples:
        entry: dict = {
            "path": s.file_path,
            "duration": s.duration_seconds or 0.0,
        }
        if s.analysis_json:
            try:
                cached = json.loads(s.analysis_json)
                if "quality" in cached:
                    entry["quality_report"] = cached["quality"]
            except json.JSONDecodeError:
                pass
        sample_dicts.append(entry)

    logger.info(
        "training_readiness_assess_start",
        profile_id=profile_id,
        sample_count=len(sample_dicts),
    )
    readiness = await assess_training_readiness(
        samples=sample_dicts,
        provider_name=profile.provider_name,
    )
    return TrainingReadinessSchema(**readiness.to_dict())
