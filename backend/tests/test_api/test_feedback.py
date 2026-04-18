"""Tests for SL-25 synthesis feedback endpoints."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.synthesis_feedback import SynthesisFeedback
from app.models.synthesis_history import SynthesisHistory


async def _create_profile(client: AsyncClient, name: str = "Feedback Test", provider: str = "kokoro") -> str:
    resp = await client.post(
        "/api/v1/profiles",
        json={"name": name, "provider_name": provider, "voice_id": "af_heart"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_history_row(db_session: AsyncSession, profile_id: str, provider: str = "kokoro") -> str:
    """Insert a SynthesisHistory row directly so the feedback endpoints have a target."""
    row = SynthesisHistory(
        profile_id=profile_id,
        provider_name=provider,
        text="hello world",
        output_path="/tmp/fake.wav",
        output_format="wav",
        duration_seconds=1.0,
        latency_ms=50,
    )
    db_session.add(row)
    await db_session.flush()
    return row.id


# ---------------------------------------------------------------------------
# POST /api/v1/synthesis/{history_id}/feedback
# ---------------------------------------------------------------------------

async def test_submit_feedback_round_trip(client: AsyncClient, db_session: AsyncSession):
    profile_id = await _create_profile(client)
    history_id = await _create_history_row(db_session, profile_id)

    resp = await client.post(
        f"/api/v1/synthesis/{history_id}/feedback",
        json={"rating": "up", "tags": ["natural", "clear"], "note": "Sounds great"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["history_id"] == history_id
    assert body["rating"] == "up"
    assert body["tags"] == ["natural", "clear"]
    assert body["note"] == "Sounds great"
    assert body["id"]

    # GET returns the same entry
    list_resp = await client.get(f"/api/v1/synthesis/{history_id}/feedback")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["rating"] == "up"
    assert items[0]["tags"] == ["natural", "clear"]


async def test_submit_feedback_unknown_history_returns_404(client: AsyncClient):
    resp = await client.post(
        "/api/v1/synthesis/does-not-exist/feedback",
        json={"rating": "down"},
    )
    assert resp.status_code == 404


async def test_submit_feedback_invalid_rating_returns_422(client: AsyncClient, db_session: AsyncSession):
    profile_id = await _create_profile(client, name="Bad rating")
    history_id = await _create_history_row(db_session, profile_id)
    resp = await client.post(
        f"/api/v1/synthesis/{history_id}/feedback",
        json={"rating": "meh"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/profiles/{profile_id}/feedback-summary
# ---------------------------------------------------------------------------

async def test_feedback_summary_aggregates_counts(client: AsyncClient, db_session: AsyncSession):
    profile_id = await _create_profile(client, name="Aggregates")
    # Create two history rows for this profile
    h1 = await _create_history_row(db_session, profile_id)
    h2 = await _create_history_row(db_session, profile_id)

    # Create feedback directly on the session so we don't depend on commit timing
    db_session.add_all([
        SynthesisFeedback(history_id=h1, rating="up"),
        SynthesisFeedback(history_id=h1, rating="up"),
        SynthesisFeedback(history_id=h2, rating="down"),
    ])
    await db_session.flush()

    resp = await client.get(f"/api/v1/profiles/{profile_id}/feedback-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile_id"] == profile_id
    assert body["up"] == 2
    assert body["down"] == 1
    assert body["total"] == 3


async def test_feedback_summary_unknown_profile(client: AsyncClient):
    resp = await client.get("/api/v1/profiles/no-such-profile/feedback-summary")
    assert resp.status_code == 404
