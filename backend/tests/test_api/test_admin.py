"""Tests for admin settings API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_settings(client: AsyncClient):
    """GET /api/v1/admin/settings returns seeded defaults."""
    # Seed first
    await client.post("/api/v1/admin/settings/seed")

    response = await client.get("/api/v1/admin/settings")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "id" in first
    assert "category" in first
    assert "key" in first
    assert "value" in first
    assert "value_type" in first
    assert "is_secret" in first


@pytest.mark.asyncio
async def test_list_settings_by_category(client: AsyncClient):
    """GET /api/v1/admin/settings/healing returns only healing settings."""
    await client.post("/api/v1/admin/settings/seed")

    response = await client.get("/api/v1/admin/settings/healing")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for setting in data:
        assert setting["category"] == "healing"


@pytest.mark.asyncio
async def test_get_single_setting(client: AsyncClient):
    """GET /api/v1/admin/settings/general/app_name returns the setting."""
    await client.post("/api/v1/admin/settings/seed")

    response = await client.get("/api/v1/admin/settings/general/app_name")
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "general"
    assert data["key"] == "app_name"
    assert data["value_type"] == "string"


@pytest.mark.asyncio
async def test_update_setting(client: AsyncClient):
    """PUT /api/v1/admin/settings/general/app_name updates the value."""
    await client.post("/api/v1/admin/settings/seed")

    response = await client.put(
        "/api/v1/admin/settings/general/app_name",
        json={"key": "app_name", "value": "Test Vox"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "Test Vox"

    # Verify it persisted
    response2 = await client.get("/api/v1/admin/settings/general/app_name")
    assert response2.json()["value"] == "Test Vox"


@pytest.mark.asyncio
async def test_bulk_update_settings(client: AsyncClient):
    """PUT /api/v1/admin/settings with bulk updates."""
    await client.post("/api/v1/admin/settings/seed")

    response = await client.put(
        "/api/v1/admin/settings",
        json={
            "category": "healing",
            "settings": [
                {"key": "health_failure_threshold", "value": "5"},
                {"key": "error_rate_spike_multiplier", "value": "4.0"},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Returns a list of updated settings
    assert isinstance(data, list)
    assert len(data) == 2

    # Verify
    resp = await client.get("/api/v1/admin/settings/healing/health_failure_threshold")
    assert resp.json()["value"] == "5"


@pytest.mark.asyncio
async def test_seed_settings(client: AsyncClient):
    """POST /api/v1/admin/settings/seed works."""
    response = await client.post("/api/v1/admin/settings/seed")
    assert response.status_code == 200
    data = response.json()
    assert "seeded" in data


@pytest.mark.asyncio
async def test_system_info(client: AsyncClient):
    """GET /api/v1/admin/system-info returns diagnostics."""
    response = await client.get("/api/v1/admin/system-info")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "app_env" in data
    assert "database_type" in data
    assert "provider_count" in data


@pytest.mark.asyncio
async def test_backup_settings(client: AsyncClient):
    """POST /api/v1/admin/backup returns export data."""
    await client.post("/api/v1/admin/settings/seed")

    response = await client.post("/api/v1/admin/backup")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "settings_count" in data
    assert data["settings_count"] > 0


@pytest.mark.asyncio
async def test_secret_masking(client: AsyncClient):
    """Secrets should be masked in list responses."""
    await client.post("/api/v1/admin/settings/seed")

    response = await client.get("/api/v1/admin/settings/auth")
    assert response.status_code == 200
    data = response.json()
    secrets = [s for s in data if s["is_secret"]]
    for secret in secrets:
        # Secret values should be masked unless the value is empty
        if secret["value"]:
            assert secret["value"] == "••••••••" or secret["value"] == ""


@pytest.mark.asyncio
async def test_get_nonexistent_setting(client: AsyncClient):
    """GET for nonexistent setting returns 404."""
    response = await client.get("/api/v1/admin/settings/general/nonexistent_key_xyz")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_setting(client: AsyncClient):
    """DELETE /api/v1/admin/settings/general/app_name removes it."""
    await client.post("/api/v1/admin/settings/seed")

    # Verify it exists
    response = await client.get("/api/v1/admin/settings/general/app_name")
    assert response.status_code == 200

    # Delete
    response = await client.delete("/api/v1/admin/settings/general/app_name")
    assert response.status_code == 200

    # Verify gone
    response = await client.get("/api/v1/admin/settings/general/app_name")
    assert response.status_code == 404
