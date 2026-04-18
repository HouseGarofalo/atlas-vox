"""Tests for the cost aggregation endpoints (VQ-39)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.synthesis_history import SynthesisHistory
from app.schemas.profile import ProfileCreate
from app.services.profile_service import create_profile


BASE = "/api/v1"


async def _seed_history(
    db: AsyncSession, profile_id: str, provider: str,
    cost: float, latency_ms: int = 200,
) -> SynthesisHistory:
    row = SynthesisHistory(
        profile_id=profile_id,
        provider_name=provider,
        text="hello",
        output_format="wav",
        duration_seconds=1.0,
        latency_ms=latency_ms,
        estimated_cost_usd=cost,
    )
    db.add(row)
    await db.flush()
    return row


@pytest.mark.asyncio
async def test_cost_endpoint_aggregates_by_provider_and_profile(
    client: AsyncClient, db_session: AsyncSession,
):
    profile_a = await create_profile(
        db_session,
        ProfileCreate(name="Cost Profile A", provider_name="elevenlabs"),
    )
    profile_b = await create_profile(
        db_session,
        ProfileCreate(name="Cost Profile B", provider_name="azure_speech"),
    )

    await _seed_history(db_session, profile_a.id, "elevenlabs", cost=0.30, latency_ms=300)
    await _seed_history(db_session, profile_a.id, "elevenlabs", cost=0.30, latency_ms=500)
    await _seed_history(db_session, profile_b.id, "azure_speech", cost=0.016, latency_ms=100)

    resp = await client.get(f"{BASE}/usage/cost")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_cost_usd"] == pytest.approx(0.616, rel=1e-3)
    assert data["total_requests"] == 3
    # Per-provider aggregation
    assert data["by_provider"]["elevenlabs"] == pytest.approx(0.60, rel=1e-3)
    assert data["by_provider"]["azure_speech"] == pytest.approx(0.016, rel=1e-3)
    # Per-profile aggregation
    assert data["by_profile"][profile_a.id] == pytest.approx(0.60, rel=1e-3)
    assert data["by_profile"][profile_b.id] == pytest.approx(0.016, rel=1e-3)


@pytest.mark.asyncio
async def test_cost_endpoint_filters_by_provider(
    client: AsyncClient, db_session: AsyncSession,
):
    profile = await create_profile(
        db_session,
        ProfileCreate(name="Filter Provider", provider_name="elevenlabs"),
    )
    await _seed_history(db_session, profile.id, "elevenlabs", cost=1.0)
    await _seed_history(db_session, profile.id, "azure_speech", cost=2.0)

    # Filter by BOTH profile_id and provider so we assert only our seeded rows
    # — other tests in this module also write azure rows via the same session
    # and the conftest savepoint cleanup runs after all tests in the module.
    resp = await client.get(
        f"{BASE}/usage/cost?provider=azure_speech&profile_id={profile.id}"
    )
    assert resp.status_code == 200
    data = resp.json()
    # Only azure rows counted, and only ones for OUR profile.
    assert "elevenlabs" not in data["by_provider"]
    assert data["by_provider"]["azure_speech"] == pytest.approx(2.0, rel=1e-3)


@pytest.mark.asyncio
async def test_cost_endpoint_filters_by_since(
    client: AsyncClient, db_session: AsyncSession,
):
    profile = await create_profile(
        db_session,
        ProfileCreate(name="Filter Since", provider_name="elevenlabs"),
    )
    # One old row, one fresh row. Only the fresh row should appear when
    # filtering by ``since`` = "tomorrow - 1s".
    old_row = await _seed_history(db_session, profile.id, "elevenlabs", cost=5.0)
    old_row.created_at = datetime.now(UTC) - timedelta(days=120)
    fresh_row = await _seed_history(db_session, profile.id, "elevenlabs", cost=1.0)
    fresh_row.created_at = datetime.now(UTC)
    await db_session.flush()

    since = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    # Use httpx `params=` so the ISO datetime's `+00:00` zone suffix gets
    # URL-encoded as `%2B00%3A00` instead of decoding to a bare space that
    # FastAPI's Query parser rejects with 422.
    resp = await client.get(
        f"{BASE}/usage/cost",
        params={"since": since, "profile_id": profile.id},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["by_provider"]["elevenlabs"] == pytest.approx(1.0, rel=1e-3)


@pytest.mark.asyncio
async def test_usage_response_includes_cost_by_provider(
    client: AsyncClient, db_session: AsyncSession,
):
    """Dashboard widget key: /usage must surface ``cost_by_provider``."""
    resp = await client.get(f"{BASE}/usage")
    assert resp.status_code == 200
    assert "cost_by_provider" in resp.json()
