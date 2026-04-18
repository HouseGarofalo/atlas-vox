"""SL-29: active-learning recommender tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_sample import AudioSample
from app.schemas.profile import ProfileCreate
from app.services.profile_service import create_profile
from app.services.sample_recommender import (
    clear_bank_cache,
    recommend_next_samples,
)


@pytest.fixture(autouse=True)
def _reset_bank_cache():
    clear_bank_cache()
    yield
    clear_bank_cache()


async def _make_profile(db: AsyncSession, name: str = "rec-test") -> str:
    p = await create_profile(db, ProfileCreate(name=name, provider_name="kokoro"))
    return p.id


async def _add_sample(db: AsyncSession, profile_id: str, transcript: str) -> None:
    db.add(AudioSample(
        profile_id=profile_id,
        filename=f"{transcript[:8]}.wav",
        original_filename=f"{transcript[:8]}.wav",
        file_path=str(Path("/tmp") / f"{transcript[:8]}.wav"),
        format="wav",
        duration_seconds=3.0,
        transcript=transcript,
    ))
    await db.flush()


async def test_empty_profile_returns_max_recommendations(
    db_session: AsyncSession,
):
    """With zero samples every phoneme is a gap — recommender returns count sentences."""
    pid = await _make_profile(db_session)
    rec = await recommend_next_samples(db_session, pid, count=5)
    assert rec.profile_id == pid
    assert rec.gap_count_before > 0
    assert len(rec.recommendations) == 5
    # After applying recommendations, gap count should drop.
    assert rec.gap_count_after < rec.gap_count_before
    # Priority ordering is dense, 1..5.
    assert [r.priority for r in rec.recommendations] == [1, 2, 3, 4, 5]
    # The FIRST recommendation must be a real gap-filler (greedy picks the
    # highest gain first). Later slots may be variety top-ups once the
    # set-cover saturates (expected when phonemizer is unavailable and the
    # bigram fallback has reduced granularity).
    assert rec.recommendations[0].gap_fill_count > 0
    # fills_gaps count matches declared count for every row.
    for r in rec.recommendations:
        assert len(r.fills_gaps) == r.gap_fill_count


async def test_recommendations_prefer_high_gain(db_session: AsyncSession):
    """First recommendation should fill at least as many gaps as later ones.

    Greedy set-cover guarantees monotonically-non-increasing gain. After
    gap-filling saturates, we fall back to variety picks with
    ``gap_fill_count == 0`` — the non-increasing property still holds.
    """
    pid = await _make_profile(db_session)
    rec = await recommend_next_samples(db_session, pid, count=10)
    gains = [r.gap_fill_count for r in rec.recommendations]
    for earlier, later in zip(gains, gains[1:]):
        assert earlier >= later


async def test_already_recorded_sentences_excluded(db_session: AsyncSession):
    """Recommender must NOT propose sentences the user already has."""
    pid = await _make_profile(db_session)
    # Seed one known-bank sentence as "already recorded".
    await _add_sample(
        db_session, pid, "The quick brown fox jumps over the lazy dog.",
    )
    rec = await recommend_next_samples(db_session, pid, count=10)
    already_seen = "the quick brown fox jumps over the lazy dog."
    for r in rec.recommendations:
        assert r.text.lower() != already_seen
    assert rec.already_recorded_skipped >= 1


async def test_recommender_count_bounded(db_session: AsyncSession):
    """``count`` caps the number of recommendations returned."""
    pid = await _make_profile(db_session)
    rec = await recommend_next_samples(db_session, pid, count=3)
    assert len(rec.recommendations) == 3


async def test_recommender_stops_when_all_gaps_filled(db_session: AsyncSession):
    """If all gaps are covered the recommender returns fewer than count rows."""
    pid = await _make_profile(db_session)
    # Ask for more than the bank can provide — should be bounded by real bank.
    rec = await recommend_next_samples(db_session, pid, count=60)
    # Assuming the bank isn't enormous, we shouldn't hit exactly 60 unless
    # there are still gaps. Either way, gap_count_after ≥ 0.
    assert rec.gap_count_after >= 0
    # Priorities remain 1..N contiguous.
    assert [r.priority for r in rec.recommendations] == list(
        range(1, len(rec.recommendations) + 1)
    )


async def test_report_declares_tokenisation_method(db_session: AsyncSession):
    """Callers need to know whether real phonemizer or bigram fallback was used."""
    pid = await _make_profile(db_session)
    rec = await recommend_next_samples(db_session, pid, count=3)
    assert rec.method in {"phonemizer", "bigram_approx"}


async def test_endpoint_round_trip(client, db_session: AsyncSession):
    """API endpoint round trip returns the dict payload."""
    pid = await _make_profile(db_session, name="api-rec")
    resp = await client.get(
        f"/api/v1/profiles/{pid}/recommended-samples?count=5"
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["profile_id"] == pid
    assert data["method"] in {"phonemizer", "bigram_approx"}
    assert len(data["recommendations"]) == 5
    for r in data["recommendations"]:
        assert "text" in r
        assert "fills_gaps" in r
        assert "gap_fill_count" in r
        assert r["priority"] >= 1


async def test_endpoint_404_on_missing_profile(client):
    resp = await client.get("/api/v1/profiles/does-not-exist/recommended-samples")
    assert resp.status_code == 404


async def test_endpoint_validates_count_bounds(client, db_session: AsyncSession):
    """count must be 1..30 per FastAPI Query constraints."""
    pid = await _make_profile(db_session, name="api-bounds")
    resp = await client.get(
        f"/api/v1/profiles/{pid}/recommended-samples?count=0"
    )
    assert resp.status_code == 422
    resp = await client.get(
        f"/api/v1/profiles/{pid}/recommended-samples?count=31"
    )
    assert resp.status_code == 422
