"""Tests for webhook endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_webhook(client: AsyncClient):
    response = await client.post("/api/v1/webhooks", json={
        "url": "https://example.com/hook",
        "events": ["training.completed"],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://example.com/hook"
    assert data["active"] is True


@pytest.mark.asyncio
async def test_list_webhooks(client: AsyncClient):
    await client.post("/api/v1/webhooks", json={"url": "https://a.com", "events": ["*"]})

    response = await client.get("/api/v1/webhooks")
    assert response.status_code == 200
    assert response.json()["count"] >= 1


@pytest.mark.asyncio
async def test_update_webhook(client: AsyncClient):
    create = await client.post("/api/v1/webhooks", json={"url": "https://b.com", "events": ["*"]})
    wid = create.json()["id"]

    response = await client.put(f"/api/v1/webhooks/{wid}", json={"active": False})
    assert response.status_code == 200
    assert response.json()["active"] is False


@pytest.mark.asyncio
async def test_delete_webhook(client: AsyncClient):
    create = await client.post("/api/v1/webhooks", json={"url": "https://c.com", "events": ["*"]})
    wid = create.json()["id"]

    response = await client.delete(f"/api/v1/webhooks/{wid}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_invalid_events_rejected(client: AsyncClient):
    response = await client.post("/api/v1/webhooks", json={
        "url": "https://d.com",
        "events": ["invalid.event"],
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_webhook_secret_excluded_from_response(client: AsyncClient):
    """Webhook response should never contain the actual secret."""
    response = await client.post("/api/v1/webhooks", json={
        "url": "https://example.com/hook",
        "events": ["training.completed"],
        "secret": "my-webhook-secret-12345",
    })
    assert response.status_code == 201
    data = response.json()

    # Secret should NOT be in response
    assert "secret" not in data or data.get("secret") is None
    # secret_set must indicate a secret is configured
    assert data.get("secret_set") is True


@pytest.mark.asyncio
async def test_webhook_no_secret_shows_secret_set_false(client: AsyncClient):
    """Webhook without secret shows secret_set=False."""
    response = await client.post("/api/v1/webhooks", json={
        "url": "https://example.com/hook2",
        "events": ["training.completed"],
    })
    assert response.status_code == 201
    data = response.json()
    assert data.get("secret_set") is False
