"""Request logging middleware with request ID tracing, timing, and telemetry."""

from __future__ import annotations

import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

# UUID pattern for path normalization - matches standard UUID format
_UUID_PATTERN = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)

import structlog
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = structlog.get_logger("atlas_vox.middleware")


# ---------------------------------------------------------------------------
# Telemetry collector — lightweight in-process metrics
# ---------------------------------------------------------------------------

@dataclass
class TelemetryMetrics:
    """In-process telemetry counters (threadsafe via GIL for single-process).

    Note: In multi-worker deployments (uvicorn --workers N), each worker
    maintains independent counters. For accurate aggregation across workers,
    use an external metrics system like Prometheus.
    """

    total_requests: int = 0
    total_errors: int = 0
    status_counts: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    endpoint_latencies: dict[str, list[float]] = field(
        default_factory=lambda: defaultdict(list)
    )
    # Keep only last N latencies per endpoint to avoid unbounded growth
    _max_latency_samples: int = 1000
    # Cap total tracked endpoint keys to prevent unbounded dict growth
    _max_tracked_endpoints: int = 500

    def record_request(
        self, method: str, path: str, status_code: int, latency_ms: float
    ) -> None:
        self.total_requests += 1
        self.status_counts[status_code] += 1
        if status_code >= 500:
            self.total_errors += 1
        normalized = _UUID_PATTERN.sub(':id', path)
        key = f"{method} {normalized}"
        # Drop new keys once the cap is reached; existing keys still accumulate samples
        if key not in self.endpoint_latencies and len(self.endpoint_latencies) >= self._max_tracked_endpoints:
            return
        samples = self.endpoint_latencies[key]
        samples.append(latency_ms)
        if len(samples) > self._max_latency_samples:
            self.endpoint_latencies[key] = samples[-self._max_latency_samples:]

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of current metrics."""
        endpoint_stats = {}
        for endpoint, latencies in self.endpoint_latencies.items():
            if latencies:
                sorted_lat = sorted(latencies)
                endpoint_stats[endpoint] = {
                    "count": len(latencies),
                    "avg_ms": round(sum(latencies) / len(latencies), 2),
                    "p50_ms": round(sorted_lat[len(sorted_lat) // 2], 2),
                    "p95_ms": round(
                        sorted_lat[int(len(sorted_lat) * 0.95)], 2
                    ),
                    "p99_ms": round(
                        sorted_lat[int(len(sorted_lat) * 0.99)], 2
                    ),
                    "max_ms": round(sorted_lat[-1], 2),
                }
        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "status_counts": dict(self.status_counts),
            "endpoints": endpoint_stats,
        }


# Singleton telemetry instance
telemetry = TelemetryMetrics()


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware:
    """Add security headers to all responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"x-xss-protection", b"0"),  # Modern browsers: rely on CSP instead
                    (b"permissions-policy", b"microphone=(), camera=(), geolocation=()"),
                ])
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------


class RequestLoggingMiddleware:
    """Pure ASGI middleware for request logging with timing and request ID tracing.

    Unlike BaseHTTPMiddleware, this does not buffer the response body, enabling
    zero-copy streaming and reducing per-request overhead.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:16])
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        logger.info(
            "request_started",
            method=method,
            path=path,
            client_ip=client_ip,
            query=str(request.url.query) if request.url.query else None,
        )

        start = time.perf_counter()
        status_code = 500  # Default in case send is never called

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                # Inject tracing headers
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                headers.append((b"x-response-time-ms", str(latency_ms).encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                "request_unhandled_exception",
                method=method,
                path=path,
                latency_ms=latency_ms,
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            telemetry.record_request(method, path, 500, latency_ms)
            raise

        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        # Record telemetry
        telemetry.record_request(method, path, status_code, latency_ms)

        # Log level based on status
        log_data = dict(
            method=method,
            path=path,
            status_code=status_code,
            latency_ms=latency_ms,
            client_ip=client_ip,
        )

        if status_code >= 500:
            logger.error("request_completed", **log_data)
        elif status_code >= 400:
            logger.warning("request_completed", **log_data)
        else:
            logger.info("request_completed", **log_data)

        structlog.contextvars.clear_contextvars()


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------


async def global_exception_handler(request: Request, exc: Exception) -> Response:
    """Catch-all exception handler that logs unhandled errors."""
    from starlette.responses import JSONResponse

    from app.core.exceptions import (
        AtlasVoxError,
        AuthenticationError,
        AuthorizationError,
        NotFoundError,
        ProviderError,
        ServiceError,
        StorageError,
        TrainingError,
        ValidationError,
    )

    request_id = getattr(request.state, "request_id", "unknown")
    
    # Handle our custom exceptions with appropriate status codes
    if isinstance(exc, NotFoundError):
        return JSONResponse(
            status_code=404,
            content={"detail": exc.detail, "request_id": request_id},
        )
    elif isinstance(exc, ValidationError):
        content = {"detail": exc.detail, "request_id": request_id}
        if exc.field:
            content["field"] = exc.field
        return JSONResponse(status_code=422, content=content)
    elif isinstance(exc, ProviderError):
        return JSONResponse(
            status_code=502,
            content={"detail": exc.detail, "request_id": request_id},
        )
    elif isinstance(exc, AuthenticationError):
        return JSONResponse(
            status_code=401,
            content={"detail": exc.detail, "request_id": request_id},
        )
    elif isinstance(exc, AuthorizationError):
        return JSONResponse(
            status_code=403,
            content={"detail": exc.detail, "request_id": request_id},
        )
    elif isinstance(exc, (StorageError, TrainingError, ServiceError)):
        return JSONResponse(
            status_code=500,
            content={"detail": exc.detail, "request_id": request_id},
        )

    # Handle any other AtlasVoxError as generic 500
    elif isinstance(exc, AtlasVoxError):
        logger.error(
            "atlas_vox_error",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            error=exc.detail,
            error_type=type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": exc.detail, "request_id": request_id},
        )
    
    # Catch-all for other exceptions
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )
