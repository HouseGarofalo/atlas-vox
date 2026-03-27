"""FastAPI router — REST endpoints for the GPU TTS service."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import structlog
from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel

from app.gpu_manager import gpu_manager
from app.providers import PROVIDER_REGISTRY
from app.providers.base import GPUProviderBase

logger = structlog.get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory provider instances (one per registered provider class)
# ---------------------------------------------------------------------------
_provider_instances: dict[str, GPUProviderBase] = {}


def _get_provider(name: str) -> GPUProviderBase:
    """Return the singleton provider instance for *name*, creating it on first access."""
    if name not in PROVIDER_REGISTRY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown provider: {name}")
    if name not in _provider_instances:
        _provider_instances[name] = PROVIDER_REGISTRY[name]()
    return _provider_instances[name]


def get_all_providers() -> dict[str, GPUProviderBase]:
    """Ensure every registered provider has an instance and return the map."""
    for name in PROVIDER_REGISTRY:
        if name not in _provider_instances:
            _provider_instances[name] = PROVIDER_REGISTRY[name]()
    return _provider_instances


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class SynthesizeRequest(BaseModel):
    text: str
    voice_id: str = "default"
    speed: float = 1.0


class LoadRequest(BaseModel):
    device: str | None = None


class CloneResponse(BaseModel):
    voice_id: str
    name: str
    provider: str
    language: str


# ---------------------------------------------------------------------------
# Provider endpoints
# ---------------------------------------------------------------------------


@router.get("/providers", summary="List all providers with capabilities")
async def list_providers() -> list[dict[str, Any]]:
    providers = get_all_providers()
    return [p.get_capabilities() for p in providers.values()]


@router.get("/providers/{name}/voices", summary="List voices for a provider")
async def list_voices(name: str) -> list[dict[str, Any]]:
    provider = _get_provider(name)
    return provider.list_voices()


@router.post("/providers/{name}/synthesize", summary="Synthesize text to audio")
async def synthesize(name: str, request: SynthesizeRequest) -> Response:
    provider = _get_provider(name)
    if not provider.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Provider '{name}' is not loaded. Call POST /providers/{name}/load first.",
        )

    try:
        audio_array, sample_rate = provider.synthesize(
            text=request.text,
            voice_id=request.voice_id,
            speed=request.speed,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    wav_bytes = _array_to_wav_bytes(audio_array, sample_rate)
    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "X-Sample-Rate": str(sample_rate),
            "X-Provider": name,
            "X-Voice-Id": request.voice_id,
        },
    )


@router.post("/providers/{name}/clone", summary="Clone voice from reference audio")
async def clone_voice(
    name: str,
    files: list[UploadFile] = File(...),
    voice_name: str = Form(""),
    language: str = Form("en"),
) -> CloneResponse:
    provider = _get_provider(name)
    if not provider.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Provider '{name}' is not loaded. Call POST /providers/{name}/load first.",
        )

    # Persist uploaded files to a temporary directory.
    sample_paths: list[Path] = []
    try:
        tmp_dir = Path(tempfile.mkdtemp(prefix="atlas_clone_"))
        for upload in files:
            dest = tmp_dir / (upload.filename or "sample.wav")
            content = await upload.read()
            dest.write_bytes(content)
            sample_paths.append(dest)

        result = provider.clone_voice(samples=sample_paths, name=voice_name, language=language)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    return CloneResponse(
        voice_id=result["voice_id"],
        name=result.get("name", ""),
        provider=result.get("provider", name),
        language=result.get("language", language),
    )


@router.post("/providers/{name}/health", summary="Health check for a provider")
async def provider_health(name: str) -> dict[str, Any]:
    provider = _get_provider(name)
    caps = provider.get_capabilities()
    return {
        "provider": name,
        "installed": caps.get("installed", False),
        "is_loaded": provider.is_loaded,
        "vram_estimate_mb": provider.vram_estimate_mb,
    }


@router.post("/providers/{name}/load", summary="Load provider model into VRAM")
async def load_provider(name: str, request: LoadRequest | None = None) -> dict[str, Any]:
    provider = _get_provider(name)
    if provider.is_loaded:
        return {"provider": name, "status": "already_loaded"}

    device = (request.device if request and request.device else None) or gpu_manager.get_device_for_provider(name)

    try:
        provider.load(device=device)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    logger.info("provider.loaded", provider=name, device=device)
    return {"provider": name, "status": "loaded", "device": device}


@router.post("/providers/{name}/unload", summary="Unload provider model from VRAM")
async def unload_provider(name: str) -> dict[str, Any]:
    provider = _get_provider(name)
    if not provider.is_loaded:
        return {"provider": name, "status": "already_unloaded"}

    provider.unload()
    logger.info("provider.unloaded", provider=name)
    return {"provider": name, "status": "unloaded"}


# ---------------------------------------------------------------------------
# GPU status
# ---------------------------------------------------------------------------


@router.get("/gpu/status", summary="GPU utilization and device info")
async def gpu_status() -> dict[str, Any]:
    return gpu_manager.get_status()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _array_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Encode a numpy audio array as WAV bytes."""
    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV", subtype="FLOAT")
    buf.seek(0)
    return buf.read()
