"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown."""
    setup_logging()
    logger.info("atlas_vox_starting", env=settings.app_env, debug=settings.debug)

    # Create tables on startup (idempotent — safe for all environments)
    await init_db()
    logger.info("database_initialized")

    from app.services.provider_registry import load_provider_configs, seed_providers

    await seed_providers()
    await load_provider_configs()
    logger.info("providers_configured")

    yield

    logger.info("atlas_vox_shutdown")


app = FastAPI(
    title="Atlas Vox",
    description="Intelligent Voice Training & Customization Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Mount API router
from app.api.v1.router import api_router  # noqa: E402
from app.mcp.transport import router as mcp_router  # noqa: E402

app.include_router(api_router)
app.include_router(mcp_router)
