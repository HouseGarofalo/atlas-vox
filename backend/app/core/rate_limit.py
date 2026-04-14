"""Rate limiting configuration using slowapi."""

from __future__ import annotations

import re

from slowapi import Limiter
from starlette.requests import Request

_IP_RE = re.compile(r"^[\da-fA-F.:]+$")


def _is_valid_ip(value: str) -> bool:
    """Basic check that a string looks like an IPv4/IPv6 address."""
    return bool(value) and len(value) <= 45 and _IP_RE.match(value) is not None


def get_client_ip(request: Request) -> str:
    """Get real client IP from trusted proxy headers.

    Prefer ``X-Real-IP`` (set by nginx to the actual connecting IP) over
    ``X-Forwarded-For`` (whose leftmost entry is client-controlled and
    trivially spoofable).  Fall back to the socket peer address.
    """
    # X-Real-IP is set by our nginx reverse proxy — most trustworthy
    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip and _is_valid_ip(real_ip):
        return real_ip

    # X-Forwarded-For: use the rightmost entry (last hop before our proxy),
    # not the leftmost (client-supplied and spoofable).
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",")]
        # Rightmost non-empty entry is the one our proxy appended
        for part in reversed(parts):
            if part and _is_valid_ip(part):
                return part

    return request.client.host if request.client else "unknown"


# General rate limiter (60 req/min per client IP)
limiter = Limiter(key_func=get_client_ip, default_limits=["60/minute"])

# Stricter rate limiter for authentication endpoints (5 req/min per client IP)
auth_limiter = Limiter(key_func=get_client_ip, default_limits=["5/minute"])
