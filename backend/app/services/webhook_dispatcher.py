"""Webhook dispatcher — fires webhooks on training events with HMAC signatures."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import socket
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Webhook event type constants
# ---------------------------------------------------------------------------
EVENT_SYNTHESIS_COMPLETE = "synthesis.complete"
EVENT_TRAINING_COMPLETE = "training.complete"
EVENT_TRAINING_COMPLETED = "training.completed"  # Legacy alias
EVENT_TRAINING_FAILED = "training.failed"
EVENT_HEALTH_ALERT = "health.alert"

ALL_EVENT_TYPES = [
    EVENT_SYNTHESIS_COMPLETE,
    EVENT_TRAINING_COMPLETE,
    EVENT_TRAINING_COMPLETED,
    EVENT_TRAINING_FAILED,
    EVENT_HEALTH_ALERT,
]

BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"}
BLOCKED_PREFIXES = ("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                    "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                    "172.30.", "172.31.", "192.168.", "169.254.")

_ALLOWED_SCHEMES = {"http", "https"}


def _is_url_safe(url: str) -> bool:
    """Reject URLs pointing to internal/private networks (SSRF protection).

    Checks performed in order:
    1. URL scheme must be http or https.
    2. Hostname blocklist (localhost variants, well-known private ranges by
       prefix, and special TLDs such as .internal / .local).
    3. DNS resolution — the hostname is resolved to all of its IP addresses
       and each one is checked against Python's ``ipaddress`` private/reserved
       detection.  This prevents SSRF via DNS rebinding or creative hostname
       aliases.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)

    # 1. Scheme validation — reject everything that isn't http(s).
    if (parsed.scheme or "").lower() not in _ALLOWED_SCHEMES:
        return False

    host = (parsed.hostname or "").lower()

    # 2. Static hostname blocklist.
    if host in BLOCKED_HOSTS:
        return False
    if any(host.startswith(p) for p in BLOCKED_PREFIXES):
        return False
    if host.endswith(".internal") or host.endswith(".local"):
        return False

    # 3. DNS resolution — resolve to IPs and block any private/reserved address.
    try:
        addr_infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, OSError):
        # DNS resolution failure — treat as unsafe to avoid silent bypass.
        logger.warning("webhook_dns_resolution_failed", host=host)
        return False

    for addr_info in addr_infos:
        # addr_info is (family, type, proto, canonname, sockaddr)
        # sockaddr is (address, port) for IPv4 and (address, port, flow, scope) for IPv6.
        ip_str = addr_info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            # Unparseable address — reject.
            return False
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            logger.warning("webhook_ssrf_ip_blocked", host=host, resolved_ip=ip_str)
            return False

    return True


def _sign_payload(payload: str, secret: str) -> str:
    """HMAC-SHA256 signature of the payload."""
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


async def dispatch_event(db: AsyncSession, event: str, data: dict) -> list[dict]:
    """Fire all active webhooks subscribed to the given event.

    Returns a list of delivery results.
    """
    result = await db.execute(
        select(Webhook).where(Webhook.active == True)  # noqa: E712
    )
    webhooks = result.scalars().all()

    logger.info(
        "dispatch_started",
        webhook_event=event,
        webhook_count=len(webhooks),
    )

    deliveries = []
    for wh in webhooks:
        # Check if webhook subscribes to this event
        subscribed_events = [e.strip() for e in wh.events.split(",")]
        if event not in subscribed_events and "*" not in subscribed_events:
            continue

        payload = json.dumps({
            "event": event,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data,
        })

        headers = {"Content-Type": "application/json"}
        if wh.secret:
            headers["X-Atlas-Vox-Signature"] = f"sha256={_sign_payload(payload, wh.secret)}"

        # SSRF protection: block internal/private URLs
        if not _is_url_safe(wh.url):
            deliveries.append({
                "webhook_id": wh.id, "url": wh.url,
                "status_code": None, "success": False,
                "error": "URL blocked: private/internal address not allowed",
            })
            logger.warning("webhook_ssrf_blocked", webhook_id=wh.id, url=wh.url)
            continue

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                resp = await client.post(wh.url, content=payload, headers=headers)
            deliveries.append({
                "webhook_id": wh.id,
                "url": wh.url,
                "status_code": resp.status_code,
                "success": 200 <= resp.status_code < 300,
            })
            logger.info("webhook_delivered", webhook_id=wh.id, webhook_event=event, status=resp.status_code)
        except Exception as e:
            logger.error("webhook_delivery_failed", webhook_id=wh.id, webhook_event=event, error=str(e))
            deliveries.append({
                "webhook_id": wh.id,
                "url": wh.url,
                "status_code": None,
                "success": False,
                "error": "Delivery failed",  # Generic message — full error logged server-side
            })

    success_count = sum(1 for d in deliveries if d.get("success"))
    logger.info(
        "dispatch_completed",
        webhook_event=event,
        total=len(deliveries),
        success=success_count,
        failed=len(deliveries) - success_count,
    )
    return deliveries


async def fire_training_completed(db: AsyncSession, job_id: str, profile_id: str, version_id: str) -> None:
    """Fire training.completed and training.complete events."""
    data = {
        "job_id": job_id,
        "profile_id": profile_id,
        "version_id": version_id,
    }
    await dispatch_event(db, EVENT_TRAINING_COMPLETED, data)
    await dispatch_event(db, EVENT_TRAINING_COMPLETE, data)


async def fire_training_failed(db: AsyncSession, job_id: str, profile_id: str, error: str) -> None:
    """Fire training.failed event."""
    await dispatch_event(db, EVENT_TRAINING_FAILED, {
        "job_id": job_id,
        "profile_id": profile_id,
        "error": error,
    })


async def fire_synthesis_complete(
    db: AsyncSession,
    synthesis_id: str,
    profile_id: str,
    provider_name: str,
    latency_ms: int,
    duration_seconds: float | None = None,
) -> None:
    """Fire synthesis.complete event after a successful synthesis."""
    await dispatch_event(db, EVENT_SYNTHESIS_COMPLETE, {
        "synthesis_id": synthesis_id,
        "profile_id": profile_id,
        "provider_name": provider_name,
        "latency_ms": latency_ms,
        "duration_seconds": duration_seconds,
    })


async def fire_health_alert(
    db: AsyncSession,
    provider_name: str,
    severity: str,
    message: str,
) -> None:
    """Fire health.alert event when a provider health issue is detected."""
    await dispatch_event(db, EVENT_HEALTH_ALERT, {
        "provider_name": provider_name,
        "severity": severity,
        "message": message,
    })
