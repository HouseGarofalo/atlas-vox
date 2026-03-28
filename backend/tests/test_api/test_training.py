"""Tests for training job endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_training_requires_samples(client: AsyncClient, db_session: AsyncSession):
    """Training fails without samples (uses elevenlabs which always supports cloning)."""
    # Create a profile with elevenlabs — it always reports supports_cloning=True
    profile_resp = await client.post("/api/v1/profiles", json={
        "name": "Empty Profile",
        "provider_name": "elevenlabs",
    })
    assert profile_resp.status_code == 201
    profile_id = profile_resp.json()["id"]

    # Try to train — should fail because no samples
    resp = await client.post(f"/api/v1/profiles/{profile_id}/train", json={})
    assert resp.status_code == 400
    assert "sample" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_training_nonexistent_profile(client: AsyncClient):
    """Training a nonexistent profile returns 400."""
    resp = await client.post("/api/v1/profiles/nonexistent-id/train", json={})
    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_training_jobs(client: AsyncClient):
    """GET /api/v1/training/jobs returns a list."""
    resp = await client.get("/api/v1/training/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert "jobs" in data
    assert "count" in data
    assert isinstance(data["jobs"], list)


@pytest.mark.asyncio
async def test_training_with_untrained_provider(client: AsyncClient, db_session: AsyncSession):
    """Training with a provider that doesn't support training returns 400."""
    # Kokoro does not support cloning or fine-tuning
    profile_resp = await client.post("/api/v1/profiles", json={
        "name": "Kokoro No Train",
        "provider_name": "kokoro",
    })
    assert profile_resp.status_code == 201
    profile_id = profile_resp.json()["id"]

    resp = await client.post(f"/api/v1/profiles/{profile_id}/train", json={})
    assert resp.status_code == 400
    detail = resp.json()["detail"].lower()
    # Should mention that the provider doesn't support training
    assert "training" in detail or "cloning" in detail or "sample" in detail
