"""Tests for presets endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_presets_seeds_defaults(client: AsyncClient):
    response = await client.get("/api/v1/presets")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 6  # 6 system presets
    names = {p["name"] for p in data["presets"]}
    assert "Friendly" in names
    assert "Professional" in names


@pytest.mark.asyncio
async def test_create_custom_preset(client: AsyncClient):
    response = await client.post("/api/v1/presets", json={
        "name": "Custom",
        "speed": 1.5,
        "pitch": 10.0,
        "volume": 0.8,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Custom"
    assert data["is_system"] is False


@pytest.mark.asyncio
async def test_cannot_delete_system_preset(client: AsyncClient):
    # Seed presets
    list_resp = await client.get("/api/v1/presets")
    system_preset = next(p for p in list_resp.json()["presets"] if p["is_system"])

    response = await client.delete(f"/api/v1/presets/{system_preset['id']}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_custom_preset(client: AsyncClient):
    create = await client.post("/api/v1/presets", json={"name": "Deletable"})
    pid = create.json()["id"]

    response = await client.delete(f"/api/v1/presets/{pid}")
    assert response.status_code == 204
