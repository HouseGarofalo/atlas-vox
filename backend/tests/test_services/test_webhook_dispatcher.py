"""Tests for the webhook dispatcher service."""

from __future__ import annotations

import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook
from app.services.webhook_dispatcher import (
    _is_url_safe,
    _sign_payload,
    dispatch_event,
)


# ---------------------------------------------------------------------------
# _is_url_safe
# ---------------------------------------------------------------------------

def test_is_url_safe_public_https():
    assert _is_url_safe("https://example.com/hook") is True


def test_is_url_safe_public_http():
    # Use a domain that actually resolves to a public IP
    assert _is_url_safe("http://example.com/callback") is True


def test_is_url_safe_localhost_hostname():
    assert _is_url_safe("http://localhost/hook") is False


def test_is_url_safe_localhost_127():
    assert _is_url_safe("http://127.0.0.1:9000/hook") is False


def test_is_url_safe_private_ip_192():
    assert _is_url_safe("http://192.168.1.100/hook") is False


def test_is_url_safe_private_ip_10():
    assert _is_url_safe("http://10.0.0.1/hook") is False


def test_is_url_safe_private_ip_172():
    assert _is_url_safe("http://172.16.0.1/hook") is False


def test_is_url_safe_internal_domain():
    assert _is_url_safe("http://myservice.internal/hook") is False


def test_is_url_safe_local_domain():
    assert _is_url_safe("http://printer.local/hook") is False


def test_is_url_safe_ipv6_loopback():
    assert _is_url_safe("http://[::1]/hook") is False


def test_is_url_safe_link_local():
    assert _is_url_safe("http://169.254.169.254/latest/meta-data") is False


# ---------------------------------------------------------------------------
# _sign_payload
# ---------------------------------------------------------------------------

def test_sign_payload_produces_hmac_sha256():
    payload = '{"event":"training.completed"}'
    secret = "my-secret-key"

    sig = _sign_payload(payload, secret)

    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    assert sig == expected


def test_sign_payload_different_secrets_produce_different_sigs():
    payload = "test payload"
    sig1 = _sign_payload(payload, "secret1")
    sig2 = _sign_payload(payload, "secret2")
    assert sig1 != sig2


def test_sign_payload_same_secret_same_payload_deterministic():
    payload = "hello"
    secret = "key"
    assert _sign_payload(payload, secret) == _sign_payload(payload, secret)


# ---------------------------------------------------------------------------
# dispatch_event — no webhooks
# ---------------------------------------------------------------------------

async def test_dispatch_no_webhooks(db_session: AsyncSession):
    """When dispatching an event with no matching non-wildcard webhooks, only wildcard webhooks fire."""
    # Deactivate all existing webhooks first to get a clean slate
    from sqlalchemy import update
    from app.models.webhook import Webhook as WebhookModel
    await db_session.execute(update(WebhookModel).values(active=False))
    await db_session.flush()

    results = await dispatch_event(db_session, "training.completed", {"job_id": "j1"})
    assert results == []


# ---------------------------------------------------------------------------
# dispatch_event — matching webhook (HTTP mocked)
# ---------------------------------------------------------------------------

async def test_dispatch_with_matching_wildcard_webhook(db_session: AsyncSession):
    webhook = Webhook(
        url="https://example.com/hook",
        events="*",
        active=True,
    )
    db_session.add(webhook)
    await db_session.flush()

    mock_response = MagicMock()
    mock_response.status_code = 200

    # httpx is imported inline inside dispatch_event — patch the class directly
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        results = await dispatch_event(db_session, "training.completed", {"job_id": "j99"})

    # Filter to only the webhook we just created (other tests may leave data)
    our_results = [r for r in results if r["webhook_id"] == webhook.id]
    assert len(our_results) == 1
    assert our_results[0]["success"] is True
    assert our_results[0]["status_code"] == 200
    assert our_results[0]["url"] == "https://example.com/hook"


async def test_dispatch_with_specific_event_match(db_session: AsyncSession):
    webhook = Webhook(
        url="https://example.com/specific",
        events="training.completed",
        active=True,
    )
    db_session.add(webhook)
    await db_session.flush()

    mock_response = MagicMock()
    mock_response.status_code = 201

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        results = await dispatch_event(db_session, "training.completed", {"job_id": "j100"})

    assert len(results) >= 1
    specific = next(r for r in results if r["url"] == "https://example.com/specific")
    assert specific["success"] is True


async def test_dispatch_webhook_not_subscribed_to_event(db_session: AsyncSession):
    """A webhook subscribed to training.failed should not fire for training.completed."""
    webhook = Webhook(
        url="https://example.com/only-failed",
        events="training.failed",
        active=True,
    )
    db_session.add(webhook)
    await db_session.flush()

    # No httpx mock needed — the webhook should not be called
    results = await dispatch_event(db_session, "training.completed", {"job_id": "j101"})

    # The webhook subscribed to training.failed should not appear in results
    assert not any(r.get("url") == "https://example.com/only-failed" for r in results)


# ---------------------------------------------------------------------------
# dispatch_event — SSRF blocked
# ---------------------------------------------------------------------------

async def test_dispatch_ssrf_blocked_localhost(db_session: AsyncSession):
    webhook = Webhook(
        url="http://localhost:8080/internal",
        events="*",
        active=True,
    )
    db_session.add(webhook)
    await db_session.flush()

    results = await dispatch_event(db_session, "training.completed", {"job_id": "j102"})

    ssrf_results = [r for r in results if r["url"] == "http://localhost:8080/internal"]
    assert len(ssrf_results) == 1
    assert ssrf_results[0]["success"] is False
    assert "blocked" in ssrf_results[0]["error"].lower()


async def test_dispatch_ssrf_blocked_private_ip(db_session: AsyncSession):
    webhook = Webhook(
        url="http://192.168.1.10/steal-data",
        events="*",
        active=True,
    )
    db_session.add(webhook)
    await db_session.flush()

    results = await dispatch_event(db_session, "training.completed", {"job_id": "j103"})

    ssrf_results = [r for r in results if r["url"] == "http://192.168.1.10/steal-data"]
    assert len(ssrf_results) == 1
    assert ssrf_results[0]["success"] is False


# ---------------------------------------------------------------------------
# dispatch_event — delivery failure
# ---------------------------------------------------------------------------

async def test_dispatch_delivery_failure(db_session: AsyncSession):
    webhook = Webhook(
        url="https://example.com/unreachable",
        events="*",
        active=True,
    )
    db_session.add(webhook)
    await db_session.flush()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))

    with patch("httpx.AsyncClient", return_value=mock_client):
        results = await dispatch_event(db_session, "training.completed", {"job_id": "j104"})

    failed = [r for r in results if r["url"] == "https://example.com/unreachable"]
    assert len(failed) == 1
    assert failed[0]["success"] is False
    assert failed[0]["status_code"] is None


# ---------------------------------------------------------------------------
# Signature header is included when secret is set
# ---------------------------------------------------------------------------

async def test_dispatch_includes_signature_header(db_session: AsyncSession):
    secret = "test-webhook-secret"
    webhook = Webhook(
        url="https://example.com/signed",
        events="*",
        active=True,
        secret=secret,
    )
    db_session.add(webhook)
    await db_session.flush()

    captured_headers: list[dict] = []

    async def _capture_post(url, content, headers):
        captured_headers.append(dict(headers))
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        return mock_resp

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = _capture_post

    with patch("httpx.AsyncClient", return_value=mock_client):
        await dispatch_event(db_session, "training.completed", {"job_id": "j105"})

    signed = [h for h in captured_headers if "X-Atlas-Vox-Signature" in h]
    assert len(signed) >= 1  # Our webhook + any pre-existing signed webhooks
    assert any(h["X-Atlas-Vox-Signature"].startswith("sha256=") for h in signed)
