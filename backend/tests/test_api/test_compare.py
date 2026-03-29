"""Tests for the comparison endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _create_ready_profile(client: AsyncClient, name: str) -> str:
    resp = await client.post("/api/v1/profiles", json={
        "name": name,
        "provider_name": "kokoro",
        "voice_id": "af_heart",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

async def test_compare_success(client: AsyncClient):
    pid_a = await _create_ready_profile(client, "Voice A")
    pid_b = await _create_ready_profile(client, "Voice B")

    mock_results = [
        {
            "profile_id": pid_a,
            "profile_name": "Voice A",
            "provider_name": "kokoro",
            "audio_url": "/api/v1/audio/cmp_a.wav",
            "duration_seconds": 1.0,
            "latency_ms": 30,
        },
        {
            "profile_id": pid_b,
            "profile_name": "Voice B",
            "provider_name": "kokoro",
            "audio_url": "/api/v1/audio/cmp_b.wav",
            "duration_seconds": 1.0,
            "latency_ms": 32,
        },
    ]

    with patch(
        "app.api.v1.endpoints.compare.compare_voices",
        new=AsyncMock(return_value=mock_results),
    ):
        resp = await client.post("/api/v1/compare", json={
            "text": "Hello comparison",
            "profile_ids": [pid_a, pid_b],
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["text"] == "Hello comparison"
    assert len(data["results"]) == 2
    profile_ids_returned = [r["profile_id"] for r in data["results"]]
    assert pid_a in profile_ids_returned
    assert pid_b in profile_ids_returned


async def test_compare_three_profiles(client: AsyncClient):
    """Comparison works with more than two profiles."""
    pids = [await _create_ready_profile(client, f"Voice {i}") for i in range(3)]

    mock_results = [
        {
            "profile_id": pid,
            "profile_name": f"Voice {i}",
            "provider_name": "kokoro",
            "audio_url": f"/api/v1/audio/cmp_{i}.wav",
            "duration_seconds": 1.0,
            "latency_ms": 30,
        }
        for i, pid in enumerate(pids)
    ]

    with patch(
        "app.api.v1.endpoints.compare.compare_voices",
        new=AsyncMock(return_value=mock_results),
    ):
        resp = await client.post("/api/v1/compare", json={
            "text": "Three voices",
            "profile_ids": pids,
        })

    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 3


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

async def test_compare_too_few_profiles(client: AsyncClient):
    """Sending only one profile_id must be rejected before hitting the service."""
    pid = await _create_ready_profile(client, "Solo Voice")

    # The CompareRequest schema has min_length=2 on profile_ids
    resp = await client.post("/api/v1/compare", json={
        "text": "Only one",
        "profile_ids": [pid],
    })
    # Pydantic validation → 422, or service raises ValueError → 400
    assert resp.status_code in (400, 422)


async def test_compare_too_few_profiles_service_error(client: AsyncClient):
    """Service layer raises ValueError for < 2 profiles."""
    pid = await _create_ready_profile(client, "Solo Voice 2")

    with patch(
        "app.api.v1.endpoints.compare.compare_voices",
        new=AsyncMock(side_effect=ValueError("At least 2 profiles required")),
    ):
        resp = await client.post("/api/v1/compare", json={
            "text": "Only one",
            "profile_ids": [pid, pid],  # pass schema validation; service raises
        })

    assert resp.status_code == 400
    assert "2" in resp.json()["detail"] or "profile" in resp.json()["detail"].lower()


async def test_compare_invalid_profile(client: AsyncClient):
    """One of the profiles does not exist → service raises ValueError → 400."""
    pid_real = await _create_ready_profile(client, "Real Voice")

    with patch(
        "app.api.v1.endpoints.compare.compare_voices",
        new=AsyncMock(side_effect=ValueError("Profile 'ghost-id' not found")),
    ):
        resp = await client.post("/api/v1/compare", json={
            "text": "Ghost profile",
            "profile_ids": [pid_real, "ghost-id"],
        })

    assert resp.status_code == 400
    assert "ghost-id" in resp.json()["detail"] or "not found" in resp.json()["detail"].lower()


async def test_compare_missing_text(client: AsyncClient):
    pid_a = await _create_ready_profile(client, "VA")
    pid_b = await _create_ready_profile(client, "VB")
    resp = await client.post("/api/v1/compare", json={"profile_ids": [pid_a, pid_b]})
    assert resp.status_code == 422


async def test_compare_exceeds_profile_limit(client: AsyncClient):
    """Requesting more than 10 profiles returns 400."""
    # Create 11 profiles
    profiles = []
    for i in range(11):
        resp = await client.post("/api/v1/profiles", json={
            "name": f"Profile {i}",
            "provider_name": "kokoro",
            "voice_id": "af_heart",
        })
        profiles.append(resp.json()["id"])

    response = await client.post("/api/v1/compare", json={
        "text": "Hello", "profile_ids": profiles,
    })
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "10" in detail or "limit" in detail
