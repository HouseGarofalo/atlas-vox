"""Aggregated voice library endpoint + preview."""

from __future__ import annotations

import hashlib
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.providers.base import SynthesisSettings
from app.services.provider_registry import PROVIDER_DISPLAY_NAMES, provider_registry

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/voices", tags=["voices"])


@router.get("")
async def list_all_voices() -> dict:
    """Aggregate voices from all available providers into a single list."""
    voices: list[dict] = []
    for name in provider_registry.list_available():
        display_name = PROVIDER_DISPLAY_NAMES.get(name, name)
        try:
            provider = provider_registry.get_provider(name)
            provider_voices = await provider.list_voices()
            for v in provider_voices:
                voices.append(
                    {
                        "voice_id": v.voice_id,
                        "name": v.name,
                        "language": v.language,
                        "gender": v.gender,
                        "provider": name,
                        "provider_display": display_name,
                    }
                )
        except Exception as exc:
            logger.warning("voice_list_failed", provider=name, error=str(exc))
            continue
    return {"voices": voices, "count": len(voices)}


# ---------- Voice Preview ----------


class VoicePreviewRequest(BaseModel):
    provider: str
    voice_id: str
    text: str | None = None


DEFAULT_PREVIEW_TEXT = "Hello, this is a preview of my voice."


@router.post("/preview")
async def preview_voice(data: VoicePreviewRequest) -> dict:
    """Synthesize a short preview for a voice and return the audio URL.

    Results are cached — if a preview file already exists it is returned
    immediately without re-synthesizing.
    """
    text = data.text or DEFAULT_PREVIEW_TEXT

    # Build a deterministic cache key
    key = f"{data.provider}_{data.voice_id}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
    preview_dir = Path(settings.storage_path) / "output" / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_file = preview_dir / f"{key}.wav"

    # Serve cached preview
    if preview_file.exists():
        filename = preview_file.name
        return {"audio_url": f"/api/v1/audio/previews/{filename}"}

    # Synthesize
    try:
        provider = provider_registry.get_provider(data.provider)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {data.provider}",
        )

    try:
        synth_settings = SynthesisSettings()
        result = await provider.synthesize(text, data.voice_id, synth_settings)

        # Move/copy result to the preview cache location
        import shutil
        shutil.copy2(str(result.audio_path), str(preview_file))

        filename = preview_file.name
        return {"audio_url": f"/api/v1/audio/previews/{filename}"}
    except Exception as exc:
        logger.error("voice_preview_failed", provider=data.provider, voice_id=data.voice_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Preview failed: {exc}",
        )
