"""API v1 router — mounts all endpoint routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    api_keys,
    audio,
    compare,
    health,
    presets,
    profiles,
    providers,
    samples,
    synthesis,
    training,
    voices,
    webhooks,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(profiles.router)
api_router.include_router(providers.router)
api_router.include_router(samples.router)
api_router.include_router(training.router)
api_router.include_router(synthesis.router)
api_router.include_router(compare.router)
api_router.include_router(audio.router)
api_router.include_router(presets.router)
api_router.include_router(api_keys.router)
api_router.include_router(voices.router)
api_router.include_router(webhooks.router)
