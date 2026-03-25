"""Audio sample endpoints — upload, list, delete, analysis, preprocessing."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import CurrentUser, DbSession
from app.models.audio_sample import AudioSample
from app.models.voice_profile import VoiceProfile
from app.schemas.sample import SampleAnalysis, SampleListResponse, SampleResponse
from app.services.audio_processor import analyze_audio

logger = structlog.get_logger(__name__)

ALLOWED_FORMATS = {"wav", "mp3", "flac", "ogg", "m4a"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB per file
MAX_FILES_PER_UPLOAD = 20

router = APIRouter(prefix="/profiles/{profile_id}/samples", tags=["samples"])


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
async def upload_samples(
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
        file_path.write_bytes(content)

        sample = AudioSample(
            profile_id=profile_id,
            filename=stored_name,
            original_filename=upload.filename,
            file_path=str(file_path),
            format=ext,
            file_size_bytes=len(content),
        )
        db.add(sample)
        await db.flush()

        logger.info("sample_uploaded", sample_id=sample.id, profile_id=profile_id, filename=upload.filename)
        created.append(SampleResponse.model_validate(sample))

    return created


@router.get("", response_model=SampleListResponse)
async def list_samples(
    profile_id: str, db: DbSession, user: CurrentUser
) -> SampleListResponse:
    """List all audio samples for a profile."""
    await _get_profile_or_404(db, profile_id)
    result = await db.execute(
        select(AudioSample)
        .where(AudioSample.profile_id == profile_id)
        .order_by(AudioSample.created_at.desc())
    )
    samples = result.scalars().all()
    return SampleListResponse(
        samples=[SampleResponse.model_validate(s) for s in samples],
        count=len(samples),
    )


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample(
    profile_id: str, sample_id: str, db: DbSession, user: CurrentUser
) -> None:
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
    logger.info("sample_deleted", sample_id=sample_id, profile_id=profile_id)


@router.get("/{sample_id}/analysis", response_model=SampleAnalysis)
async def get_sample_analysis(
    profile_id: str, sample_id: str, db: DbSession, user: CurrentUser
) -> SampleAnalysis:
    """Return audio analysis (pitch, energy, duration) for a sample.

    Runs analysis on demand and caches in the DB.
    """
    sample = await _get_sample_or_404(db, profile_id, sample_id)

    # Use cached analysis if available
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
