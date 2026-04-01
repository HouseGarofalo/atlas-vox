"""Audio enhancement and voice design endpoints backed by ElevenLabs advanced APIs.

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
"""

from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from app.core.dependencies import CurrentUser, DbSession

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


@router.post("/speech-to-speech", response_model=SpeechToSpeechResponse)
async def speech_to_speech(
    audio: UploadFile,
    user: CurrentUser,
    voice_id: str = Query(..., description="Target ElevenLabs voice ID"),
) -> SpeechToSpeechResponse:
    """Convert the voice in an uploaded audio file to a different ElevenLabs voice.

    Accepts any common audio format (wav, mp3, flac, ogg, m4a).
    Returns a URL to the converted MP3.
    """
    from app.core.config import settings as app_settings

    if not audio.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    # Write upload to a temp path in the output directory
    tmp_dir = Path(app_settings.storage_path) / "output"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    import uuid

    ext = audio.filename.rsplit(".", 1)[-1].lower() if "." in audio.filename else "bin"
    tmp_path = tmp_dir / f"sts_input_{uuid.uuid4().hex[:12]}.{ext}"

    content = await audio.read()
    tmp_path.write_bytes(content)

    provider = _require_elevenlabs_provider()
    logger.info("speech_to_speech_requested", voice_id=voice_id, input_size=len(content))

    try:
        output_path = await provider.speech_to_speech(tmp_path, voice_id)
    except Exception as exc:
        logger.error("speech_to_speech_failed", voice_id=voice_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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


@router.post("/design-voice", response_model=DesignVoiceResponse)
async def design_voice(
    user: CurrentUser,
    description: str = Query(..., description="Natural-language description of the desired voice"),
    text: str = Query("", description="Optional sample text for preview"),
) -> DesignVoiceResponse:
    """Generate voice previews from a natural-language description.

    Returns up to 3 generated voice previews with their generated_voice_id
    and base64-encoded audio for immediate playback.
    """
    provider = _require_elevenlabs_provider()
    logger.info("design_voice_requested", description=description[:80])

    try:
        result = await provider.design_voice(description=description, text=text)
    except Exception as exc:
        logger.error("design_voice_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice design failed: {exc}",
        ) from exc

    logger.info("design_voice_completed", preview_count=len(result.get("previews", [])))
    return DesignVoiceResponse(previews=result.get("previews", []))


@router.post("/sound-effect", response_model=SoundEffectResponse)
async def generate_sound_effect(
    user: CurrentUser,
    description: str = Query(..., description="Text description of the desired sound effect"),
    duration: float = Query(5.0, ge=1.0, le=22.0, description="Duration in seconds (1–22)"),
) -> SoundEffectResponse:
    """Generate a sound effect MP3 from a text description.

    Uses ElevenLabs Sound Effects API. Duration must be between 1 and 22 seconds.
    """
    provider = _require_elevenlabs_provider()
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
