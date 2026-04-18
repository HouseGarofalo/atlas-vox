"""VQ-36 — quality dashboard aggregation tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_sample import AudioSample
from app.models.model_version import ModelVersion
from app.models.synthesis_feedback import SynthesisFeedback
from app.models.synthesis_history import SynthesisHistory
from app.models.voice_profile import VoiceProfile
from app.schemas.profile import ProfileCreate
from app.services.profile_service import create_profile
from app.services.quality_dashboard import build_quality_dashboard


async def _make_profile(db: AsyncSession, name: str = "QD") -> VoiceProfile:
    return await create_profile(db, ProfileCreate(name=name, provider_name="kokoro"))


async def _add_history(
    db: AsyncSession, profile_id: str, *, wer: float | None = None, days_ago: int = 0,
) -> SynthesisHistory:
    row = SynthesisHistory(
        profile_id=profile_id,
        provider_name="kokoro",
        text="hello",
        output_format="wav",
        duration_seconds=1.0,
        latency_ms=100,
        quality_wer=wer,
    )
    db.add(row)
    await db.flush()
    if days_ago:
        row.created_at = datetime.now(UTC) - timedelta(days=days_ago)
        await db.flush()
    return row


async def _add_version(
    db: AsyncSession, profile_id: str, number: int, *, metrics: dict | None = None,
) -> ModelVersion:
    v = ModelVersion(
        profile_id=profile_id,
        version_number=number,
        provider_model_id=f"pm-{number}",
        metrics_json=json.dumps(metrics) if metrics else None,
    )
    db.add(v)
    await db.flush()
    return v


async def _add_feedback(db: AsyncSession, history_id: str, rating: str) -> None:
    db.add(SynthesisFeedback(history_id=history_id, rating=rating))
    await db.flush()


async def _add_sample(
    db: AsyncSession, profile_id: str, *, passed: bool | None,
) -> None:
    analysis = None
    if passed is not None:
        analysis = json.dumps({"passed": passed})
    db.add(AudioSample(
        profile_id=profile_id,
        filename=f"{profile_id[:6]}-{passed}.wav",
        original_filename=f"{profile_id[:6]}-{passed}.wav",
        file_path=str(Path("/tmp") / f"{profile_id[:6]}.wav"),
        format="wav",
        duration_seconds=5.0,
        analysis_json=analysis,
    ))
    await db.flush()


async def test_missing_profile_raises(db_session: AsyncSession):
    with pytest.raises(ValueError):
        await build_quality_dashboard(db_session, "no-such-profile")


async def test_empty_profile_returns_neutral_score(db_session: AsyncSession):
    """A brand-new profile with no data gets a 50 neutral overall score."""
    p = await _make_profile(db_session, name="empty")
    report = await build_quality_dashboard(db_session, p.id)
    assert report.profile_id == p.id
    assert report.synthesis_count == 0
    assert report.overall_score == pytest.approx(50.0, abs=0.5)
    assert report.wer_series == []
    assert report.version_metrics == []
    assert report.rating_distribution.total == 0
    assert report.sample_health.total == 0
    # Should carry warnings so the UI can surface "not enough data yet".
    assert any("Whisper-check" in w or "versions" in w for w in report.warnings)


async def test_wer_series_returned_chronologically(db_session: AsyncSession):
    p = await _make_profile(db_session, name="wer")
    await _add_history(db_session, p.id, wer=0.4, days_ago=3)
    await _add_history(db_session, p.id, wer=0.2, days_ago=2)
    await _add_history(db_session, p.id, wer=0.1, days_ago=1)
    # One row without quality_wer — must be excluded from the chart.
    await _add_history(db_session, p.id, wer=None)

    report = await build_quality_dashboard(db_session, p.id)
    assert len(report.wer_series) == 3
    # Oldest → newest.
    assert [round(p.quality_wer, 2) for p in report.wer_series] == [0.40, 0.20, 0.10]
    assert report.recent_wer == pytest.approx(0.10)


async def test_wer_limit_caps_chart_size(db_session: AsyncSession):
    p = await _make_profile(db_session, name="wer-cap")
    for i in range(30):
        await _add_history(db_session, p.id, wer=0.1 + 0.01 * i, days_ago=30 - i)
    report = await build_quality_dashboard(db_session, p.id, wer_limit=5)
    assert len(report.wer_series) == 5


async def test_version_metrics_populated_and_active_flag(db_session: AsyncSession):
    p = await _make_profile(db_session, name="vm")
    v1 = await _add_version(db_session, p.id, 1, metrics={
        "method": "clone", "quality_wer": 0.15, "mos": 3.5,
    })
    v2 = await _add_version(db_session, p.id, 2, metrics={
        "method": "clone", "quality_wer": 0.08, "mos": 4.1,
        "speaker_similarity": 0.88, "is_regression": False,
    })
    # Manually mark v2 active.
    p.active_version_id = v2.id
    await db_session.flush()

    report = await build_quality_dashboard(db_session, p.id)
    assert [m.version_number for m in report.version_metrics] == [1, 2]
    assert report.version_metrics[0].is_active is False
    assert report.version_metrics[1].is_active is True
    assert report.version_metrics[1].speaker_similarity == pytest.approx(0.88)
    assert report.version_metrics[1].is_regression is False
    assert report.active_version_id == v2.id
    # v1 metrics should not bleed into v2's fields.
    assert report.version_metrics[0].speaker_similarity is None


async def test_malformed_metrics_json_warns_and_continues(db_session: AsyncSession):
    p = await _make_profile(db_session, name="bad-metrics")
    v = await _add_version(db_session, p.id, 1)
    v.metrics_json = "not valid json"
    await db_session.flush()
    report = await build_quality_dashboard(db_session, p.id)
    assert len(report.version_metrics) == 1
    assert any("malformed" in w for w in report.warnings)


async def test_rating_distribution_aggregated(db_session: AsyncSession):
    p = await _make_profile(db_session, name="ratings")
    h1 = await _add_history(db_session, p.id)
    h2 = await _add_history(db_session, p.id)
    h3 = await _add_history(db_session, p.id)
    await _add_feedback(db_session, h1.id, "up")
    await _add_feedback(db_session, h2.id, "up")
    await _add_feedback(db_session, h3.id, "down")

    report = await build_quality_dashboard(db_session, p.id)
    assert report.rating_distribution.up == 2
    assert report.rating_distribution.down == 1
    assert report.rating_distribution.total == 3
    assert report.rating_distribution.up_pct == pytest.approx(66.666, abs=0.1)


async def test_sample_health_breakdown(db_session: AsyncSession):
    p = await _make_profile(db_session, name="health")
    await _add_sample(db_session, p.id, passed=True)
    await _add_sample(db_session, p.id, passed=True)
    await _add_sample(db_session, p.id, passed=False)
    await _add_sample(db_session, p.id, passed=None)  # unknown — no analysis

    report = await build_quality_dashboard(db_session, p.id)
    assert report.sample_health.total == 4
    assert report.sample_health.passed == 2
    assert report.sample_health.failed == 1
    assert report.sample_health.unknown == 1
    # pass_rate is over judged samples only.
    assert report.sample_health.pass_rate_pct == pytest.approx(66.666, abs=0.1)


async def test_overall_score_reflects_quality(db_session: AsyncSession):
    """Good WER + positive ratings + passing samples → high overall score."""
    p = await _make_profile(db_session, name="good")
    # Great WER data.
    for i in range(5):
        await _add_history(db_session, p.id, wer=0.05)
    # All thumbs up.
    h = await _add_history(db_session, p.id, wer=0.05)
    await _add_feedback(db_session, h.id, "up")
    await _add_feedback(db_session, h.id, "up")
    # All samples pass.
    await _add_sample(db_session, p.id, passed=True)
    await _add_sample(db_session, p.id, passed=True)

    report = await build_quality_dashboard(db_session, p.id)
    assert report.overall_score > 90

    # Inverse profile: bad on every axis → low score.
    bad = await _make_profile(db_session, name="bad")
    for _ in range(5):
        await _add_history(db_session, bad.id, wer=0.6)
    h2 = await _add_history(db_session, bad.id, wer=0.6)
    await _add_feedback(db_session, h2.id, "down")
    await _add_feedback(db_session, h2.id, "down")
    await _add_sample(db_session, bad.id, passed=False)

    bad_report = await build_quality_dashboard(db_session, bad.id)
    assert bad_report.overall_score < 30


async def test_endpoint_returns_dashboard(client, db_session: AsyncSession):
    p = await _make_profile(db_session, name="endpoint")
    await _add_history(db_session, p.id, wer=0.12)
    resp = await client.get(f"/api/v1/profiles/{p.id}/quality-dashboard")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["profile_id"] == p.id
    assert "overall_score" in data
    assert "wer_series" in data
    assert "rating_distribution" in data
    assert "sample_health" in data


async def test_endpoint_404_for_missing_profile(client):
    resp = await client.get("/api/v1/profiles/does-not-exist/quality-dashboard")
    assert resp.status_code == 404
