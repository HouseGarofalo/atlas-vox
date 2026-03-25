"""Provider management endpoints."""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, HTTPException, status

from app.schemas.provider import (
    ProviderCapabilitiesSchema,
    ProviderHealthSchema,
    ProviderListResponse,
    ProviderResponse,
)
from app.services.provider_registry import provider_registry

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=ProviderListResponse)
async def list_providers() -> ProviderListResponse:
    """List all known TTS providers with implementation status."""
    providers = []
    for info in provider_registry.list_all_known():
        caps = None
        if info["implemented"]:
            try:
                raw_caps = await provider_registry.get_capabilities(info["name"])
                caps = ProviderCapabilitiesSchema(**raw_caps.__dict__)
            except Exception:
                pass

        providers.append(
            ProviderResponse(
                id=info["name"],
                name=info["name"],
                display_name=info["display_name"],
                provider_type=info["provider_type"],
                enabled=info["implemented"],
                gpu_mode=caps.gpu_mode if caps else "none",
                capabilities=caps,
                health=None,
                created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
        )
    return ProviderListResponse(providers=providers, count=len(providers))


@router.get("/{name}")
async def get_provider(name: str) -> ProviderResponse:
    """Get details for a specific provider."""
    known = {p["name"]: p for p in provider_registry.list_all_known()}
    if name not in known:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Provider '{name}' not found")

    info = known[name]
    caps = None
    if info["implemented"]:
        try:
            raw_caps = await provider_registry.get_capabilities(name)
            caps = ProviderCapabilitiesSchema(**raw_caps.__dict__)
        except Exception:
            pass

    from datetime import datetime
    return ProviderResponse(
        id=name,
        name=name,
        display_name=info["display_name"],
        provider_type=info["provider_type"],
        enabled=info["implemented"],
        gpu_mode=caps.gpu_mode if caps else "none",
        capabilities=caps,
        health=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@router.post("/{name}/health", response_model=ProviderHealthSchema)
async def check_provider_health(name: str) -> ProviderHealthSchema:
    """Run a health check on a provider."""
    available = provider_registry.list_available()
    if name not in available:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{name}' not available",
        )

    health = await provider_registry.health_check(name)
    return ProviderHealthSchema(**health.__dict__)


@router.get("/{name}/voices")
async def list_provider_voices(name: str) -> dict:
    """List available voices for a provider."""
    available = provider_registry.list_available()
    if name not in available:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{name}' not available",
        )

    provider = provider_registry.get_provider(name)
    voices = await provider.list_voices()
    return {
        "provider": name,
        "voices": [{"voice_id": v.voice_id, "name": v.name, "language": v.language} for v in voices],
        "count": len(voices),
    }
