"""Rate limiting configuration using slowapi."""

from __future__ import annotations

from slowapi import Limiter
from starlette.requests import Request


def get_client_ip(request: Request) -> str:
    """Get real client IP, respecting proxy headers.

    When running behind a reverse proxy (nginx, Traefik, etc.) the default
    ``request.client.host`` returns the internal Docker/proxy IP.  This
    function checks standard proxy headers first.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


# General rate limiter (60 req/min per client IP)
limiter = Limiter(key_func=get_client_ip, default_limits=["60/minute"])

# Stricter rate limiter for authentication endpoints (5 req/min per client IP)
auth_limiter = Limiter(key_func=get_client_ip, default_limits=["5/minute"])
