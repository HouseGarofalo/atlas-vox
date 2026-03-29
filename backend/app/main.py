"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import get_logger, setup_logging
from app.core.middleware import (
    RequestLoggingMiddleware,
    global_exception_handler,
    telemetry,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown."""
    setup_logging()
    logger.info("atlas_vox_starting", env=settings.app_env, debug=settings.debug)

    # Create tables on startup (idempotent — safe for all environments)
    await init_db()
    logger.info("database_initialized")

    # Verify Redis connectivity
    try:
        import redis

        r = redis.Redis.from_url(settings.redis_url, socket_timeout=3)
        r.ping()
        logger.info("redis_connected", url=settings.redis_url, db=r.connection_pool.connection_kwargs.get("db", 0))
    except Exception as exc:
        logger.warning("redis_unavailable", url=settings.redis_url, error=str(exc))

    from app.services.provider_registry import (
        discover_gpu_providers,
        load_provider_configs,
        seed_providers,
    )

    await seed_providers()
    await load_provider_configs()
    await discover_gpu_providers()
    logger.info("providers_configured")

    # Start self-healing engine
    from app.healing.engine import healing_engine
    await healing_engine.start()
    logger.info("self_healing_started")

    yield

    # Stop self-healing engine
    await healing_engine.stop()

    # Graceful shutdown
    from app.core.database import engine
    await engine.dispose()
    logger.info("database_engine_disposed")
    logger.info("atlas_vox_shutdown")


app = FastAPI(
    title="Atlas Vox",
    description="Intelligent Voice Training & Customization Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# Request logging & telemetry middleware (outermost — wraps everything)
app.add_middleware(RequestLoggingMiddleware)

# GZip compression for responses >= 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
)

# Global exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Rate limiting
from app.core.rate_limit import limiter  # noqa: E402
from slowapi import _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- Telemetry endpoint ---
@app.get("/api/v1/telemetry", tags=["telemetry"])
async def get_telemetry() -> dict:
    """Return in-process telemetry metrics snapshot."""
    return telemetry.snapshot()


# Mount API router
from app.api.v1.router import api_router  # noqa: E402
from app.mcp.transport import router as mcp_router  # noqa: E402

# OpenAI-compatible TTS endpoint (mounted at /v1/audio/speech, not /api/v1)
from app.api.v1.endpoints.openai_compat import router as openai_compat_router  # noqa: E402

from app.healing.endpoints import router as healing_router  # noqa: E402

app.include_router(api_router)
app.include_router(mcp_router)
app.include_router(openai_compat_router)
app.include_router(healing_router, prefix="/api/v1")
