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
    from app.core.exceptions import ValidationError
    pid = await _make_profile(db_session, "Solo")

    with pytest.raises(ValidationError, match="[Aa]t least 2"):
        await compare_voices(db_session, text="test", profile_ids=[pid])


async def test_compare_zero_profiles(db_session: AsyncSession):
    from app.core.exceptions import ValidationError
    with pytest.raises(ValidationError, match="[Aa]t least 2"):
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


async def test_compare_three_profiles_runs_concurrently_and_returns_all(
    db_session: AsyncSession,
):
    """P2-24: comparison with 3+ profiles must dispatch concurrently and
    return one entry per profile_id even under interleaved completion.

    The test asserts:
      1. exactly 3 result rows (one per profile_id)
      2. each profile_id appears exactly once
      3. results preserve a consistent shape
      4. synthesize() was invoked once per profile
    """
    pids = [
        await _make_profile(db_session, f"Concurrent Profile {i}") for i in range(3)
    ]

    call_log: list[str] = []

    async def _staggered_synthesize(db, *, text, profile_id, **kwargs):
        # Simulate different latencies so completion order ≠ call order.
        import asyncio
        delay = 0.02 * (pids.index(profile_id) + 1)
        await asyncio.sleep(delay)
        call_log.append(profile_id)
        return {
            "id": f"h-{profile_id}",
            "audio_url": f"/api/v1/audio/{profile_id}.wav",
            "duration_seconds": 1.0,
            "latency_ms": int(delay * 1000),
            "profile_id": profile_id,
            "provider_name": "kokoro",
        }

    with patch("app.services.comparison_service.synthesize", side_effect=_staggered_synthesize):
        results = await compare_voices(
            db_session,
            text="Race three voices",
            profile_ids=pids,
        )

    # 1. all three ran
    assert len(results) == 3
    # 2. one entry per profile id
    returned = sorted(r["profile_id"] for r in results)
    assert returned == sorted(pids)
    # 3. clean shape — no errors
    for r in results:
        assert "error" not in r
        assert r["audio_url"].endswith(".wav")
        assert r["duration_seconds"] == 1.0
    # 4. synthesize called exactly once per profile
    assert sorted(call_log) == sorted(pids)


async def test_compare_five_profiles_mixed_success_and_failure(
    db_session: AsyncSession,
):
    """P2-24: 5-way comparison where two profiles fail must still return
    exactly 5 entries, with the 2 failures tagged and 3 successes intact.
    """
    pids = [
        await _make_profile(db_session, f"Profile 5-{i}") for i in range(5)
    ]
    failing = {pids[1], pids[3]}

    async def _mixed(db, *, text, profile_id, **kwargs):
        if profile_id in failing:
            raise RuntimeError(f"boom: {profile_id}")
        return {
            "id": f"h-{profile_id}",
            "audio_url": f"/api/v1/audio/{profile_id}.wav",
            "duration_seconds": 2.0,
            "latency_ms": 25,
            "profile_id": profile_id,
            "provider_name": "kokoro",
        }

    with patch("app.services.comparison_service.synthesize", side_effect=_mixed):
        results = await compare_voices(
            db_session,
            text="Hello",
            profile_ids=pids,
        )

    assert len(results) == 5
    errors = [r for r in results if "error" in r]
    successes = [r for r in results if "error" not in r]
    assert len(errors) == 2
    assert len(successes) == 3
    assert {r["profile_id"] for r in errors} == failing


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
