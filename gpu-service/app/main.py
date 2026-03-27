"""Atlas Vox GPU Service — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.gpu_manager import gpu_manager
from app.router import get_all_providers, router

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Structlog configuration
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(structlog, 'get_level_from_name', lambda x: 20)(settings.log_level)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle."""
    # -- Startup --
    logger.info(
        "gpu_service.starting",
        host=settings.host,
        port=settings.port,
        default_device=settings.default_device,
    )

    # Log GPU status.
    status_info = gpu_manager.get_status()
    if status_info["cuda_available"]:
        for dev in status_info["devices"]:
            logger.info(
                "gpu.detected",
                index=dev["index"],
                name=dev["name"],
                vram_total_mb=dev["total_vram_mb"],
                vram_free_mb=dev["free_vram_mb"],
            )
    else:
        logger.warning("gpu.no_cuda", msg="No CUDA devices found — GPU providers will not be loadable")

    # Auto-load configured providers.
    if settings.auto_load_providers:
        providers = get_all_providers()
        for name in settings.auto_load_providers:
            if name not in providers:
                logger.warning("auto_load.unknown_provider", provider=name)
                continue
            provider = providers[name]
            caps = provider.get_capabilities()
            if not caps.get("installed", False):
                logger.warning("auto_load.not_installed", provider=name)
                continue
            try:
                device = gpu_manager.get_device_for_provider(name)
                provider.load(device=device)
                logger.info("auto_load.success", provider=name, device=device)
            except Exception as exc:
                logger.error("auto_load.failed", provider=name, error=str(exc))

    logger.info("gpu_service.ready")
    yield

    # -- Shutdown --
    logger.info("gpu_service.shutting_down")
    providers = get_all_providers()
    for name, provider in providers.items():
        if provider.is_loaded:
            try:
                provider.unload()
                logger.info("shutdown.unloaded", provider=name)
            except Exception as exc:
                logger.error("shutdown.unload_failed", provider=name, error=str(exc))
    logger.info("gpu_service.stopped")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Atlas Vox GPU Service",
    description="GPU-accelerated TTS provider service for Atlas Vox",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", summary="Service health check")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "atlas-vox-gpu-service",
        "version": "0.1.0",
        "cuda_available": gpu_manager.get_status()["cuda_available"],
    }
