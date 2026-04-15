"""Audio enhancement, voice design, and Audio Design Studio endpoints.

Endpoints
---------
POST /audio-tools/isolate
    Remove background noise from a stored audio sample.

POST /audio-tools/speech-to-speech
    Convert the voice in an uploaded audio file to a different ElevenLabs voice.

POST /audio-tools/design-voice
    Generate voice previews from a natural-language description.

POST /audio-tools/sound-effect
    Generate a sound effect MP3 from a text description.

POST /audio-tools/upload
    Upload an audio file for processing in the Audio Design Studio.

GET  /audio-tools/files
    List uploaded working files.

DELETE /audio-tools/files/{file_id}
    Delete a working file.

POST /audio-tools/trim
    Trim an audio file to start/end timestamps.

POST /audio-tools/concat
    Concatenate multiple audio files.

POST /audio-tools/effects
    Apply an effects chain (noise reduction, normalize, trim silence, gain).

POST /audio-tools/export
    Export a processed audio file in a target format/sample rate.

POST /audio-tools/analyze
    Run quality analysis on an uploaded file.

POST /audio-tools/isolate-file
    Run audio isolation on an uploaded working file (ElevenLabs).
"""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.audio_tools import (
    MAX_UPLOAD_BYTES,
    AnalyzeRequest,
    AnalyzeResponse,
    AudioFileInfo,
    AudioFileListResponse,
    AudioQualityBrief,
    AudioUploadResponse,
    ConcatRequest,
    EffectsChainRequest,
    ExportRequest,
    ExportResponse,
    IsolateFileRequest,
    IsolateFileResponse,
    QualityIssueBrief,
    TrimRequest,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/audio-tools", tags=["audio-tools"])

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class IsolateAudioRequest(BaseModel):
    profile_id: str
    sample_id: str


class IsolateAudioResponse(BaseModel):
    output_filename: str
    audio_url: str


class SpeechToSpeechResponse(BaseModel):
    output_filename: str
    audio_url: str


class DesignVoiceResponse(BaseModel):
    previews: list[dict]


class SoundEffectResponse(BaseModel):
    output_filename: str
    audio_url: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_elevenlabs_provider():
    """Return the ElevenLabs provider or raise 400 if not available."""
    try:
        from app.services.provider_registry import provider_registry

        provider = provider_registry.get_provider("elevenlabs")
        return provider
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ElevenLabs provider not available: {exc}",
        )


def _audio_url(filename: str) -> str:
    """Build a relative URL for serving a generated audio file."""
    return f"/api/v1/audio/{filename}"


def _design_audio_url(filename: str) -> str:
    """Build a relative URL for serving an Audio Design Studio file."""
    return f"/api/v1/audio/design/{filename}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/isolate", response_model=IsolateAudioResponse)
async def isolate_audio(
    request: IsolateAudioRequest,
    db: DbSession,
    user: CurrentUser,
) -> IsolateAudioResponse:
    """Remove background noise from a stored sample using ElevenLabs Audio Isolation.

    The cleaned file is written alongside the original sample on disk and its
    URL is returned.
    """
    from sqlalchemy import select

    from app.models.audio_sample import AudioSample
    from app.models.voice_profile import VoiceProfile

    # Validate profile exists
    profile_result = await db.execute(
        select(VoiceProfile).where(VoiceProfile.id == request.profile_id)
    )
    if profile_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    # Validate sample belongs to profile
    sample_result = await db.execute(
        select(AudioSample).where(
            AudioSample.id == request.sample_id,
            AudioSample.profile_id == request.profile_id,
        )
    )
    sample = sample_result.scalar_one_or_none()
    if sample is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

    provider = _require_elevenlabs_provider()
    source_path = Path(sample.file_path)

    if not source_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample file not found on disk",
        )

    logger.info("audio_isolation_requested", sample_id=request.sample_id, profile_id=request.profile_id)

    try:
        output_path = await provider.isolate_audio(source_path)
    except Exception as exc:
        logger.error("audio_isolation_failed", sample_id=request.sample_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio isolation failed: {exc}",
        ) from exc

    logger.info("audio_isolation_completed", output=str(output_path))
    return IsolateAudioResponse(
        output_filename=output_path.name,
        audio_url=_audio_url(output_path.name),
    )


STS_SUPPORTED_PROVIDERS = {"elevenlabs"}


@router.post("/speech-to-speech", response_model=SpeechToSpeechResponse)
async def speech_to_speech(
    audio: UploadFile,
    user: CurrentUser,
    voice_id: str = Query(..., description="Target voice ID on the selected provider"),
    provider_name: str | None = Query(
        None,
        description="Provider to use for speech-to-speech. Defaults to elevenlabs.",
    ),
) -> SpeechToSpeechResponse:
    """Convert the voice in an uploaded audio file to a different voice.

    Only providers that implement ``speech_to_speech`` are supported
    (currently: ElevenLabs). Accepts any common audio format
    (wav, mp3, flac, ogg, m4a, webm). Returns a URL to the converted audio.
    """
    from app.core.config import settings as app_settings

    # ---- Validate provider before touching disk / spending memory ----
    effective_provider = (provider_name or "elevenlabs").lower()
    if effective_provider not in STS_SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Speech-to-speech is not available for provider '{effective_provider}'. "
                f"Supported providers: {', '.join(sorted(STS_SUPPORTED_PROVIDERS))}."
            ),
        )

    if not audio.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    # Write upload to a temp path in the output directory
    tmp_dir = Path(app_settings.storage_path) / "output"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    ext = audio.filename.rsplit(".", 1)[-1].lower() if "." in audio.filename else "bin"
    tmp_path = tmp_dir / f"sts_input_{uuid.uuid4().hex[:12]}.{ext}"

    content = await audio.read()
    max_s2s_bytes = 50 * 1024 * 1024  # 50MB limit for speech-to-speech
    if len(content) > max_s2s_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum {max_s2s_bytes // (1024 * 1024)}MB for speech-to-speech.",
        )
    tmp_path.write_bytes(content)

    provider = _require_elevenlabs_provider()
    logger.info(
        "speech_to_speech_requested",
        voice_id=voice_id,
        provider=effective_provider,
        input_size=len(content),
    )

    try:
        output_path = await provider.speech_to_speech(tmp_path, voice_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("speech_to_speech_failed", voice_id=voice_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Speech-to-speech conversion failed: {exc}",
        ) from exc
    finally:
        # Always clean up the temp input file
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    logger.info("speech_to_speech_completed", output=str(output_path))
    return SpeechToSpeechResponse(
        output_filename=output_path.name,
        audio_url=_audio_url(output_path.name),
    )


class DesignVoiceRequest(BaseModel):
    description: str
    text: str = ""


@router.post("/design-voice", response_model=DesignVoiceResponse)
async def design_voice(
    body: DesignVoiceRequest,
    user: CurrentUser,
) -> DesignVoiceResponse:
    """Generate voice previews from a natural-language description.

    Returns up to 3 generated voice previews with their generated_voice_id
    and base64-encoded audio for immediate playback.
    """
    provider = _require_elevenlabs_provider()
    logger.info("design_voice_requested", description=body.description[:80])

    try:
        result = await provider.design_voice(description=body.description, text=body.text)
    except Exception as exc:
        logger.error("design_voice_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice design failed: {exc}",
        ) from exc

    logger.info("design_voice_completed", preview_count=len(result.get("previews", [])))
    return DesignVoiceResponse(previews=result.get("previews", []))


class SoundEffectRequest(BaseModel):
    description: str
    duration_seconds: float = 5.0


@router.post("/sound-effect", response_model=SoundEffectResponse)
async def generate_sound_effect(
    body: SoundEffectRequest,
    user: CurrentUser,
) -> SoundEffectResponse:
    """Generate a sound effect MP3 from a text description.

    Uses ElevenLabs Sound Effects API. Duration must be between 1 and 22 seconds.
    """
    provider = _require_elevenlabs_provider()
    description = body.description
    duration = body.duration_seconds
    logger.info("sound_effect_requested", description=description[:80], duration=duration)

    try:
        output_path = await provider.generate_sound_effect(description=description, duration=duration)
    except Exception as exc:
        logger.error("sound_effect_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sound effect generation failed: {exc}",
        ) from exc

    logger.info("sound_effect_completed", output=str(output_path))
    return SoundEffectResponse(
        output_filename=output_path.name,
        audio_url=_audio_url(output_path.name),
    )


# ---------------------------------------------------------------------------
# Audio Design Studio endpoints
# ---------------------------------------------------------------------------

ALLOWED_AUDIO_EXTENSIONS = {"wav", "mp3", "ogg", "flac", "m4a", "aac", "wma", "webm"}


def _workdir() -> Path:
    """Return (and create) the audio design working directory."""
    from app.core.config import settings as app_settings

    d = Path(app_settings.storage_path) / "audio-design"
    d.mkdir(parents=True, exist_ok=True)
    return d


_FILE_ID_RE = re.compile(r"^[a-f0-9]{16}$")


def _file_path(file_id: str) -> Path:
    """Resolve a file_id to a path inside the workdir, or raise 404."""
    if not _FILE_ID_RE.match(file_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file_id format")
    wd = _workdir()
    candidates = list(wd.glob(f"{file_id}.*"))
    if not candidates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {file_id}")
    return candidates[0]


def _build_file_info(path: Path, file_id: str) -> AudioFileInfo:
    """Build an AudioFileInfo from a file on disk."""
    from app.services.audio_processor import _get_audio_info_sync

    info = _get_audio_info_sync(path)
    return AudioFileInfo(
        file_id=file_id,
        filename=path.name,
        original_filename=path.name,
        duration_seconds=info["duration_seconds"],
        sample_rate=info["sample_rate"],
        channels=info["channels"],
        format=info["format"],
        file_size_bytes=info["file_size_bytes"],
        audio_url=_design_audio_url(path.name),
    )


async def _build_file_info_async(path: Path, file_id: str) -> AudioFileInfo:
    """Async wrapper for building file info."""
    from app.services.audio_processor import get_audio_info

    info = await get_audio_info(path)
    return AudioFileInfo(
        file_id=file_id,
        filename=path.name,
        original_filename=path.name,
        duration_seconds=info["duration_seconds"],
        sample_rate=info["sample_rate"],
        channels=info["channels"],
        format=info["format"],
        file_size_bytes=info["file_size_bytes"],
        audio_url=_design_audio_url(path.name),
    )


@router.post("/upload", response_model=AudioUploadResponse)
async def upload_audio(
    audio: UploadFile,
    user: CurrentUser,
) -> AudioUploadResponse:
    """Upload an audio file for processing in the Audio Design Studio."""
    if not audio.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")

    ext = audio.filename.rsplit(".", 1)[-1].lower() if "." in audio.filename else ""
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: .{ext}. Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}",
        )

    file_id = uuid.uuid4().hex[:16]
    wd = _workdir()
    dest = wd / f"{file_id}.{ext}"

    content = await audio.read()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024 * 1024)}MB",
        )
    dest.write_bytes(content)

    logger.info("audio_design_upload", file_id=file_id, filename=audio.filename, size=len(content))

    file_info = await _build_file_info_async(dest, file_id)
    file_info.original_filename = audio.filename or dest.name

    # Run quality analysis
    quality_brief: AudioQualityBrief | None = None
    try:
        from app.services.audio_quality import validate_audio_quality

        report = await validate_audio_quality(dest)
        quality_brief = AudioQualityBrief(
            passed=report.passed,
            score=report.score,
            snr_db=report.metrics.get("snr_db"),
            rms_db=report.metrics.get("rms_db"),
            issues=[QualityIssueBrief(code=i.code, severity=i.severity, message=i.message) for i in report.issues],
        )
    except Exception as exc:
        logger.warning("audio_design_quality_failed", file_id=file_id, error=str(exc))

    return AudioUploadResponse(file=file_info, quality=quality_brief)


@router.get("/files", response_model=AudioFileListResponse)
async def list_files(
    user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> AudioFileListResponse:
    """List working files in the Audio Design Studio (paginated)."""
    wd = _workdir()
    all_paths = sorted(
        (p for p in wd.iterdir() if p.is_file() and p.suffix.lstrip(".").lower() in ALLOWED_AUDIO_EXTENSIONS),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    total = len(all_paths)
    page = all_paths[skip : skip + limit]

    files: list[AudioFileInfo] = []
    for p in page:
        file_id = p.stem
        try:
            info = await _build_file_info_async(p, file_id)
            files.append(info)
        except (ValueError, IOError, RuntimeError) as exc:
            logger.warning("audio_design_file_info_failed", path=str(p), error=type(exc).__name__)
    return AudioFileListResponse(files=files, count=len(files), total=total)


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(file_id: str, user: CurrentUser):
    """Delete a working file."""
    path = _file_path(file_id)
    path.unlink(missing_ok=True)
    logger.info("audio_design_file_deleted", file_id=file_id)


@router.post("/trim", response_model=AudioUploadResponse)
async def trim_audio_endpoint(
    body: TrimRequest,
    user: CurrentUser,
) -> AudioUploadResponse:
    """Trim an audio file to [start_seconds, end_seconds]."""
    from app.services.audio_processor import trim_audio

    source = _file_path(body.file_id)
    out_id = uuid.uuid4().hex[:16]
    ext = source.suffix
    out_path = _workdir() / f"{out_id}{ext}"

    try:
        await trim_audio(source, out_path, body.start_seconds, body.end_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    file_info = await _build_file_info_async(out_path, out_id)
    return AudioUploadResponse(file=file_info)


@router.post("/concat", response_model=AudioUploadResponse)
async def concat_audio_endpoint(
    body: ConcatRequest,
    user: CurrentUser,
) -> AudioUploadResponse:
    """Concatenate multiple audio files into one."""
    from app.services.audio_processor import concat_audio

    paths = [_file_path(fid) for fid in body.file_ids]
    out_id = uuid.uuid4().hex[:16]
    out_path = _workdir() / f"{out_id}.wav"

    try:
        await concat_audio(paths, out_path, body.crossfade_ms)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    file_info = await _build_file_info_async(out_path, out_id)
    return AudioUploadResponse(file=file_info)


@router.post("/effects", response_model=AudioUploadResponse)
async def apply_effects_endpoint(
    body: EffectsChainRequest,
    user: CurrentUser,
) -> AudioUploadResponse:
    """Apply a chain of audio effects to a file.

    Supported effects: noise_reduction, normalize, trim_silence, gain.
    Effects are applied in the order specified.
    """
    from app.services.audio_processor import (
        PreprocessConfig,
        apply_gain,
        preprocess_audio,
    )

    source = _file_path(body.file_id)
    current = source
    intermediates: list[Path] = []

    for effect in body.effects:
        out_id = uuid.uuid4().hex[:16]
        out_path = _workdir() / f"{out_id}.wav"

        if effect.type == "noise_reduction":
            config = PreprocessConfig(
                noise_reduction_strength=effect.strength or 0.5,
                normalize=False,
                trim_silence=False,
            )
            await preprocess_audio(current, out_path, config)

        elif effect.type == "normalize":
            config = PreprocessConfig(
                noise_reduction_strength=0.0,
                normalize=True,
                trim_silence=False,
            )
            await preprocess_audio(current, out_path, config)

        elif effect.type == "trim_silence":
            config = PreprocessConfig(
                noise_reduction_strength=0.0,
                normalize=False,
                trim_silence=True,
                silence_threshold_db=effect.threshold_db or -40.0,
            )
            await preprocess_audio(current, out_path, config)

        elif effect.type == "gain":
            await apply_gain(current, out_path, effect.gain_db or 0.0)

        # Track intermediate files for cleanup (not source, not final)
        if current != source:
            intermediates.append(current)
        current = out_path

    # Clean up intermediate files (keep source and final output)
    for tmp in intermediates:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            logger.warning("audio_design_cleanup_failed", path=str(tmp))

    final_id = current.stem
    file_info = await _build_file_info_async(current, final_id)
    return AudioUploadResponse(file=file_info)


@router.post("/export", response_model=ExportResponse)
async def export_audio_endpoint(
    body: ExportRequest,
    user: CurrentUser,
) -> ExportResponse:
    """Export a working file in the requested format and sample rate."""
    from app.services.audio_processor import convert_format, get_audio_info

    source = _file_path(body.file_id)
    fmt = body.format.value
    out_id = uuid.uuid4().hex[:16]
    out_path = _workdir() / f"{out_id}.{fmt}"

    result_path = await convert_format(source, out_path, fmt, body.sample_rate)
    info = await get_audio_info(result_path)

    return ExportResponse(
        file_id=out_id,
        filename=result_path.name,
        audio_url=_design_audio_url(result_path.name),
        format=fmt,
        sample_rate=info["sample_rate"],
        duration_seconds=info["duration_seconds"],
        file_size_bytes=info["file_size_bytes"],
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_audio_endpoint(
    body: AnalyzeRequest,
    user: CurrentUser,
) -> AnalyzeResponse:
    """Run quality and spectral analysis on a working file."""
    from app.services.audio_processor import analyze_audio
    from app.services.audio_quality import validate_audio_quality

    source = _file_path(body.file_id)

    analysis = await analyze_audio(source)
    report = await validate_audio_quality(source)

    return AnalyzeResponse(
        file_id=body.file_id,
        duration_seconds=analysis.duration_seconds,
        sample_rate=analysis.sample_rate,
        quality=AudioQualityBrief(
            passed=report.passed,
            score=report.score,
            snr_db=report.metrics.get("snr_db"),
            rms_db=report.metrics.get("rms_db"),
            issues=[QualityIssueBrief(code=i.code, severity=i.severity, message=i.message) for i in report.issues],
        ),
        pitch_mean=analysis.pitch_mean,
        pitch_std=analysis.pitch_std,
        energy_mean=analysis.energy_mean,
        energy_std=analysis.energy_std,
        spectral_centroid_mean=analysis.spectral_centroid_mean,
        rms_db=analysis.rms_db,
    )


@router.post("/isolate-file", response_model=IsolateFileResponse)
async def isolate_file_endpoint(
    body: IsolateFileRequest,
    user: CurrentUser,
) -> IsolateFileResponse:
    """Run ElevenLabs audio isolation on a working file (not tied to a profile)."""
    source = _file_path(body.file_id)
    provider = _require_elevenlabs_provider()

    logger.info("audio_design_isolate", file_id=body.file_id)
    try:
        output_path = await provider.isolate_audio(source)
    except Exception as exc:
        logger.error("audio_design_isolate_failed", file_id=body.file_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio isolation failed: {exc}",
        ) from exc

    # Copy output into workdir with new ID, then clean up provider output
    out_id = uuid.uuid4().hex[:16]
    dest = _workdir() / f"{out_id}{output_path.suffix}"
    shutil.copy2(str(output_path), str(dest))

    # Clean up the provider's temporary output file
    if output_path.exists() and output_path != source:
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("audio_design_isolate_cleanup_failed", path=str(output_path))

    file_info = await _build_file_info_async(dest, out_id)
    return IsolateFileResponse(file=file_info)
