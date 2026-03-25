"""Webhook dispatcher — fires webhooks on training events with HMAC signatures."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook

logger = structlog.get_logger(__name__)

BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"}
BLOCKED_PREFIXES = ("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                    "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                    "172.30.", "172.31.", "192.168.", "169.254.")


def _is_url_safe(url: str) -> bool:
    """Reject URLs pointing to internal/private networks (SSRF protection)."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in BLOCKED_HOSTS:
        return False
    if any(host.startswith(p) for p in BLOCKED_PREFIXES):
        return False
    if host.endswith(".internal") or host.endswith(".local"):
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
            logger.info("webhook_delivered", webhook_id=wh.id, event=event, status=resp.status_code)
        except Exception as e:
            logger.error("webhook_delivery_failed", webhook_id=wh.id, event=event, error=str(e))
            deliveries.append({
                "webhook_id": wh.id,
                "url": wh.url,
                "status_code": None,
                "success": False,
                "error": "Delivery failed",  # Generic message — full error logged server-side
            })

    return deliveries


async def fire_training_completed(db: AsyncSession, job_id: str, profile_id: str, version_id: str) -> None:
    """Fire training.completed event."""
    await dispatch_event(db, "training.completed", {
        "job_id": job_id,
        "profile_id": profile_id,
        "version_id": version_id,
    })


async def fire_training_failed(db: AsyncSession, job_id: str, profile_id: str, error: str) -> None:
    """Fire training.failed event."""
    await dispatch_event(db, "training.failed", {
        "job_id": job_id,
        "profile_id": profile_id,
        "error": error,
    })
