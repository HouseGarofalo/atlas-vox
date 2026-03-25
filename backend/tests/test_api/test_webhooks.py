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
