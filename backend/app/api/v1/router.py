"""API v1 router — mounts all endpoint routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    api_keys,
    audio,
    audio_tools,
    audiobook,
    auth,
    compare,
    consent,
    favorites,
    health,
    presets,
    profiles,
    pronunciation,
    providers,
    samples,
    stt,
    synthesis,
    text_import,
    training,
    usage,
    voices,
    webhooks,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(profiles.router)
api_router.include_router(providers.router)
api_router.include_router(samples.router)
api_router.include_router(audio_tools.router)
api_router.include_router(training.router)
api_router.include_router(synthesis.router)
api_router.include_router(compare.router)
api_router.include_router(audio.router)
api_router.include_router(presets.router)
api_router.include_router(api_keys.router)
api_router.include_router(voices.router)
api_router.include_router(webhooks.router)
api_router.include_router(pronunciation.router)
api_router.include_router(usage.router)
api_router.include_router(favorites.router)
api_router.include_router(text_import.router)
api_router.include_router(consent.router)
api_router.include_router(stt.router)
api_router.include_router(audiobook.router)
