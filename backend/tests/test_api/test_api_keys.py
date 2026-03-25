"""Tests for API key endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient):
    response = await client.post("/api/v1/api-keys", json={
        "name": "Test Key",
        "scopes": ["read", "synthesize"],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Key"
    assert data["key"].startswith("avx_")
    assert data["key_prefix"] == data["key"][:12]
    assert set(data["scopes"]) == {"read", "synthesize"}


@pytest.mark.asyncio
async def test_list_api_keys_masked(client: AsyncClient):
    await client.post("/api/v1/api-keys", json={"name": "K1", "scopes": ["read"]})

    response = await client.get("/api/v1/api-keys")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    # Full key should NOT be in list response
    for k in data["api_keys"]:
        assert len(k["key_prefix"]) <= 12


@pytest.mark.asyncio
async def test_revoke_api_key(client: AsyncClient):
    create = await client.post("/api/v1/api-keys", json={"name": "Revokable", "scopes": ["read"]})
    kid = create.json()["id"]

    response = await client.delete(f"/api/v1/api-keys/{kid}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_invalid_scopes_rejected(client: AsyncClient):
    response = await client.post("/api/v1/api-keys", json={
        "name": "Bad",
        "scopes": ["read", "invalid_scope"],
    })
    assert response.status_code == 400
