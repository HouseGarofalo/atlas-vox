"""OpenAI-compatible TTS API — drop-in replacement for /v1/audio/speech.

Any tool that supports OpenAI's TTS API (LangChain, CrewAI, etc.) can use
Atlas Vox by pointing its base_url at this server.
"""

from __future__ import annotations

import io
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.providers.base import SynthesisSettings
from app.services.provider_registry import provider_registry

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["openai-compat"])

# ---------------------------------------------------------------------------
# Voice & model mapping tables
# ---------------------------------------------------------------------------

# Map OpenAI canonical voice names to (provider, voice_id)
OPENAI_VOICE_MAP: dict[str, tuple[str, str]] = {
    "alloy": ("kokoro", "af_alloy"),
    "echo": ("kokoro", "am_echo"),
    "fable": ("kokoro", "bm_fable"),
    "onyx": ("kokoro", "am_onyx"),
    "nova": ("kokoro", "af_nova"),
    "shimmer": ("kokoro", "af_sky"),
}

# Map model identifiers to provider names
MODEL_MAP: dict[str, str] = {
    "tts-1": "kokoro",
    "tts-1-hd": "elevenlabs",
    "kokoro": "kokoro",
    "elevenlabs": "elevenlabs",
    "azure": "azure_speech",
    "azure_speech": "azure_speech",
    "xtts": "coqui_xtts",
    "coqui": "coqui_xtts",
    "coqui_xtts": "coqui_xtts",
    "piper": "piper",
    "styletts2": "styletts2",
    "cosyvoice": "cosyvoice",
    "dia": "dia",
    "dia2": "dia2",
}

AUDIO_MEDIA_TYPES: dict[str, str] = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "opus": "audio/opus",
    "flac": "audio/flac",
    "aac": "audio/aac",
    "pcm": "audio/pcm",
}

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class SpeechRequest(BaseModel):
    """OpenAI-compatible speech request body."""

    model: str = "tts-1"
    input: str  # noqa: A003  — matches OpenAI field name
    voice: str = "alloy"
    response_format: str = Field(default="mp3", alias="response_format")
    speed: float = 1.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_voice(model: str, voice: str) -> tuple[str, str]:
    """Resolve (model, voice) to (provider_name, voice_id)."""
    # Check OpenAI canonical voice map first
    if voice in OPENAI_VOICE_MAP:
        mapped_provider, mapped_voice = OPENAI_VOICE_MAP[voice]
        # If user explicitly chose a non-default model, honour that
        provider = MODEL_MAP.get(model, mapped_provider)
        # Only use the mapped voice when the provider is the one the map targets
        if provider == mapped_provider:
            return provider, mapped_voice
        return provider, voice
    # Fall through: use model to pick provider, voice passes through as-is
    provider = MODEL_MAP.get(model, model)
    return provider, voice


def _convert_audio(audio_bytes: bytes, from_format: str, to_format: str) -> bytes:
    """Best-effort audio format conversion via pydub (ffmpeg).

    Returns *audio_bytes* unchanged if pydub/ffmpeg are not available or the
    conversion fails.
    """
    if from_format == to_format:
        return audio_bytes
    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=from_format)
        buf = io.BytesIO()
        audio.export(buf, format=to_format)
        return buf.getvalue()
    except Exception as exc:
        logger.warning(
            "audio_conversion_fallback",
            from_format=from_format,
            to_format=to_format,
            error=str(exc),
        )
        return audio_bytes  # Return original if conversion fails


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/audio/speech")
async def create_speech(request: SpeechRequest) -> StreamingResponse:
    """OpenAI-compatible text-to-speech endpoint.

    Returns the synthesised audio as a binary stream — compatible with the
    OpenAI Python SDK, LangChain, CrewAI, and any other client that speaks
    the ``POST /v1/audio/speech`` contract.
    """
    provider_name, voice_id = _resolve_voice(request.model, request.voice)

    # Validate provider
    try:
        provider = provider_registry.get_provider(provider_name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown provider '{provider_name}' (resolved from model='{request.model}'). "
                f"Available: {', '.join(provider_registry.list_available())}"
            ),
        )

    # Synthesize
    try:
        settings = SynthesisSettings(speed=request.speed)
        result = await provider.synthesize(request.input, voice_id, settings)
    except Exception as exc:
        logger.error(
            "openai_compat_synthesis_error",
            provider=provider_name,
            voice=voice_id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synthesis failed: {exc}",
        )

    # Read audio bytes
    audio_bytes = result.audio_path.read_bytes()

    # Convert format if the provider output doesn't match the requested format
    if request.response_format != result.format:
        audio_bytes = _convert_audio(audio_bytes, result.format, request.response_format)

    media_type = AUDIO_MEDIA_TYPES.get(request.response_format, "audio/wav")

    return StreamingResponse(
        iter([audio_bytes]),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=speech.{request.response_format}",
        },
    )


@router.get("/models")
async def list_models() -> dict[str, Any]:
    """OpenAI-compatible models list.

    Returns the set of 'models' that a client can pass in the ``model``
    field of a speech request.
    """
    available = provider_registry.list_available()
    data: list[dict[str, str]] = []

    # Always include the OpenAI-style aliases
    static_models = [
        {
            "id": "tts-1",
            "object": "model",
            "owned_by": "atlas-vox",
            "description": "Kokoro TTS (fast, CPU)",
        },
        {
            "id": "tts-1-hd",
            "object": "model",
            "owned_by": "atlas-vox",
            "description": "ElevenLabs (high quality, cloud)",
        },
    ]
    data.extend(static_models)

    # Add each available provider as a model
    for name in available:
        # Skip duplicates already covered by the static aliases
        if name in {m["id"] for m in data}:
            continue
        data.append({
            "id": name,
            "object": "model",
            "owned_by": "atlas-vox",
        })

    return {"object": "list", "data": data}
