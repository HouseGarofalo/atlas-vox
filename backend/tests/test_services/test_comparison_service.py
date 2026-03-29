"""Tests for the comparison service layer."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.profile import ProfileCreate
from app.services.comparison_service import compare_voices
from app.services.profile_service import create_profile


async def _make_profile(db: AsyncSession, name: str) -> str:
    profile = await create_profile(db, ProfileCreate(
        name=name,
        provider_name="kokoro",
        voice_id="af_heart",
    ))
    return profile.id


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

async def test_compare_too_few_profiles(db_session: AsyncSession):
    """compare_voices raises ValueError when fewer than 2 profile IDs are given."""
    pid = await _make_profile(db_session, "Solo")

    with pytest.raises(ValueError, match="[Aa]t least 2"):
        await compare_voices(db_session, text="test", profile_ids=[pid])


async def test_compare_zero_profiles(db_session: AsyncSession):
    with pytest.raises(ValueError, match="[Aa]t least 2"):
        await compare_voices(db_session, text="test", profile_ids=[])


async def test_compare_invalid_profile(db_session: AsyncSession):
    """A non-existent profile_id returns error entries (no longer raises ValueError
    since pre-validation was removed — errors are captured per-profile in results)."""
    pid_real = await _make_profile(db_session, "Real")

    results = await compare_voices(
        db_session,
        text="test",
        profile_ids=[pid_real, "ghost-does-not-exist"],
    )
    # The ghost profile should produce an error entry
    ghost_result = [r for r in results if r["profile_id"] == "ghost-does-not-exist"]
    assert len(ghost_result) == 1
    assert "error" in ghost_result[0]


async def test_compare_both_profiles_invalid(db_session: AsyncSession):
    """All-invalid profiles return error entries for each."""
    results = await compare_voices(
        db_session,
        text="test",
        profile_ids=["fake-1", "fake-2"],
    )
    assert len(results) == 2
    assert all("error" in r for r in results)


# ---------------------------------------------------------------------------
# Happy path (synthesis mocked)
# ---------------------------------------------------------------------------

async def test_compare_success(db_session: AsyncSession):
    pid_a = await _make_profile(db_session, "Compare A")
    pid_b = await _make_profile(db_session, "Compare B")

    side_effects = [
        {
            "id": "h1",
            "audio_url": "/api/v1/audio/cmp_a.wav",
            "duration_seconds": 1.0,
            "latency_ms": 30,
            "profile_id": pid_a,
            "provider_name": "kokoro",
        },
        {
            "id": "h2",
            "audio_url": "/api/v1/audio/cmp_b.wav",
            "duration_seconds": 1.0,
            "latency_ms": 35,
            "profile_id": pid_b,
            "provider_name": "kokoro",
        },
    ]

    results_iter = iter(side_effects)

    async def _mock_synthesize(db, *, text, profile_id, **kwargs):
        return next(results_iter)

    with patch("app.services.comparison_service.synthesize", side_effect=_mock_synthesize):
        results = await compare_voices(
            db_session,
            text="Hello comparison",
            profile_ids=[pid_a, pid_b],
        )

    assert len(results) == 2
    returned_ids = [r["profile_id"] for r in results]
    assert pid_a in returned_ids
    assert pid_b in returned_ids
    # No error key on success
    for r in results:
        assert "error" not in r


async def test_compare_returns_error_entry_on_synthesis_failure(db_session: AsyncSession):
    """When one synthesis fails the service logs the error and includes an error entry."""
    pid_a = await _make_profile(db_session, "Good Voice")
    pid_b = await _make_profile(db_session, "Bad Voice")

    async def _fail_second(db, *, text, profile_id, **kwargs):
        if profile_id == pid_b:
            raise RuntimeError("synthesis exploded")
        return {
            "id": "h1",
            "audio_url": "/api/v1/audio/good.wav",
            "duration_seconds": 1.0,
            "latency_ms": 20,
            "profile_id": pid_a,
            "provider_name": "kokoro",
        }

    with patch("app.services.comparison_service.synthesize", side_effect=_fail_second):
        results = await compare_voices(
            db_session,
            text="Partial failure",
            profile_ids=[pid_a, pid_b],
        )

    assert len(results) == 2
    error_entries = [r for r in results if "error" in r]
    assert len(error_entries) == 1
    assert error_entries[0]["profile_id"] == pid_b
