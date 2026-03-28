"""Tests for profile CRUD endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_profile(client: AsyncClient):
    response = await client.post("/api/v1/profiles", json={
        "name": "Test Voice",
        "provider_name": "kokoro",
        "language": "en",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Voice"
    assert data["provider_name"] == "kokoro"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_list_profiles(client: AsyncClient):
    # Create a profile first
    await client.post("/api/v1/profiles", json={"name": "P1", "provider_name": "kokoro"})

    response = await client.get("/api/v1/profiles")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert len(data["profiles"]) >= 1


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient):
    create = await client.post("/api/v1/profiles", json={"name": "P2", "provider_name": "kokoro"})
    pid = create.json()["id"]

    response = await client.get(f"/api/v1/profiles/{pid}")
    assert response.status_code == 200
    assert response.json()["name"] == "P2"


@pytest.mark.asyncio
async def test_get_nonexistent_profile(client: AsyncClient):
    response = await client.get("/api/v1/profiles/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient):
    create = await client.post("/api/v1/profiles", json={"name": "P3", "provider_name": "kokoro"})
    pid = create.json()["id"]

    response = await client.put(f"/api/v1/profiles/{pid}", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_profile(client: AsyncClient):
    create = await client.post("/api/v1/profiles", json={"name": "P4", "provider_name": "kokoro"})
    pid = create.json()["id"]

    response = await client.delete(f"/api/v1/profiles/{pid}")
    assert response.status_code == 204

    get_response = await client.get(f"/api/v1/profiles/{pid}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_create_profile_with_voice_id(client: AsyncClient):
    """Creating a profile with voice_id sets status to ready."""
    resp = await client.post("/api/v1/profiles", json={
        "name": "Test Library Voice",
        "provider_name": "kokoro",
        "voice_id": "af_heart",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "ready"
    assert data["voice_id"] == "af_heart"


@pytest.mark.asyncio
async def test_create_profile_without_voice_id_is_pending(client: AsyncClient):
    """Creating a profile without voice_id sets status to pending."""
    resp = await client.post("/api/v1/profiles", json={
        "name": "Custom Voice",
        "provider_name": "kokoro",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["voice_id"] is None
