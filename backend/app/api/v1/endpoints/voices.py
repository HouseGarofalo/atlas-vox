"""Aggregated voice library endpoint + preview."""


import hashlib
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.dependencies import CurrentUser
from app.core.rate_limit import limiter
from app.providers.base import SynthesisSettings
from app.services.provider_registry import PROVIDER_DISPLAY_NAMES, provider_registry

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/voices", tags=["voices"])


@router.get("")
async def list_all_voices(
    user: CurrentUser,
    limit: int = Query(default=1000, le=5000),
    offset: int = Query(default=0, ge=0),
) -> JSONResponse:
    """Aggregate voices from all available providers into a single list."""
    logger.info("list_all_voices_called", limit=limit, offset=offset)
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
    total = len(voices)
    paginated = voices[offset : offset + limit]
    logger.info("list_all_voices_returned", total=total, count=len(paginated))
    return JSONResponse(
        content={"voices": paginated, "count": len(paginated), "total": total},
        headers={"Cache-Control": "public, max-age=300"},
    )


# ---------- Voice Preview ----------


class VoicePreviewRequest(BaseModel):
    provider: str
    voice_id: str
    text: str | None = None


DEFAULT_PREVIEW_TEXT = "Hello, this is a preview of my voice."


@router.post("/preview")
@limiter.limit("10/minute")
async def preview_voice(request: Request, data: VoicePreviewRequest, user: CurrentUser) -> dict:
    """Synthesize a short preview for a voice and return the audio URL.

    Results are cached — if a preview file already exists it is returned
    immediately without re-synthesizing.
    """
    logger.info("preview_voice_called", provider=data.provider, voice_id=data.voice_id)
    text = data.text or DEFAULT_PREVIEW_TEXT

    # Build a deterministic cache key
    key = f"{data.provider}_{data.voice_id}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
    preview_dir = Path(settings.storage_path) / "output" / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_file = preview_dir / f"{key}.wav"

    # Serve cached preview
    if preview_file.exists():
        filename = preview_file.name
        logger.info("preview_voice_cache_hit", provider=data.provider, voice_id=data.voice_id)
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
        logger.info("preview_voice_synthesized", provider=data.provider, voice_id=data.voice_id)
        return {"audio_url": f"/api/v1/audio/previews/{filename}"}
    except NotImplementedError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Provider '{data.provider}' does not support synthesis for this voice.",
        )
    except Exception as exc:
        error_msg = str(exc).lower()
        # Provide user-friendly errors for common failure modes
        if "not configured" in error_msg or "api_key" in error_msg or "subscription" in error_msg:
            detail = f"Provider '{data.provider}' requires an API key. Configure it in Settings > Providers."
        elif "model" in error_msg and ("not found" in error_msg or "download" in error_msg or "connection" in error_msg):
            detail = f"Provider '{data.provider}' model is not available. It may need to download first."
        else:
            detail = f"Preview failed for '{data.provider}'. Check server logs."
        logger.error("voice_preview_failed", provider=data.provider, voice_id=data.voice_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )
