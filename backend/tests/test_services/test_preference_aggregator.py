"""Tests for SL-26 preference aggregator."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.synthesis_feedback import SynthesisFeedback
from app.models.synthesis_history import SynthesisHistory
from app.schemas.profile import ProfileCreate
from app.services.preference_aggregator import (
    NumericRange,
    PreferenceSummary,
    TextCharacteristics,
    aggregate_preferences,
    summary_to_json,
)
from app.services.profile_service import create_profile


async def _make_profile(db: AsyncSession, name: str = "Pref Test"):
    return await create_profile(
        db,
        ProfileCreate(name=name, provider_name="kokoro", voice_id="af_heart"),
    )


def _settings(speed: float, pitch: float, voice_settings: dict | None = None) -> str:
    payload: dict = {"speed": speed, "pitch": pitch, "volume": 1.0, "preset_id": None}
    if voice_settings:
        payload["voice_settings"] = voice_settings
    return json.dumps(payload)


async def _add_history(
    db: AsyncSession,
    profile_id: str,
    text: str,
    settings_json: str,
) -> SynthesisHistory:
    row = SynthesisHistory(
        profile_id=profile_id,
        provider_name="kokoro",
        text=text,
        output_path="/tmp/fake.wav",
        output_format="wav",
        duration_seconds=1.0,
        latency_ms=10,
        settings_json=settings_json,
    )
    db.add(row)
    await db.flush()
    return row


async def _add_feedback(
    db: AsyncSession, history_id: str, rating: str
) -> SynthesisFeedback:
    row = SynthesisFeedback(history_id=history_id, rating=rating)
    db.add(row)
    await db.flush()
    return row


# ---------------------------------------------------------------------------
# Aggregator correctness
# ---------------------------------------------------------------------------

async def test_aggregate_empty_profile_returns_zero_counts(db_session: AsyncSession):
    profile = await _make_profile(db_session, name="Empty Pref")
    summary = await aggregate_preferences(db_session, profile.id)

    assert summary.profile_id == profile.id
    assert summary.total_up == 0
    assert summary.total_down == 0
    assert summary.favored_voice_settings == {}
    assert summary.favored_text.sample_count == 0


async def test_aggregate_combines_up_settings_and_text(db_session: AsyncSession):
    profile = await _make_profile(db_session, name="Combo Pref")

    # Three "up" syntheses with different speed/pitch; one "down" synthesis
    h1 = await _add_history(db_session, profile.id, "hello world",
                            _settings(speed=1.0, pitch=0.0))
    h2 = await _add_history(db_session, profile.id, "hello kind world",
                            _settings(speed=1.2, pitch=2.0))
    h3 = await _add_history(db_session, profile.id, "another sample",
                            _settings(speed=0.8, pitch=-2.0))
    h_down = await _add_history(
        db_session, profile.id,
        "this one is bad", _settings(speed=2.0, pitch=10.0),
    )

    await _add_feedback(db_session, h1.id, "up")
    await _add_feedback(db_session, h2.id, "up")
    await _add_feedback(db_session, h3.id, "up")
    await _add_feedback(db_session, h_down.id, "down")

    summary = await aggregate_preferences(db_session, profile.id)

    assert summary.total_up == 3
    assert summary.total_down == 1

    # Favored ranges: mean of (1.0, 1.2, 0.8) = 1.0; stdev > 0
    speed_range = summary.favored_voice_settings["speed"]
    assert speed_range.count == 3
    assert speed_range.mean == pytest.approx(1.0, abs=1e-6)
    assert speed_range.stdev > 0.0

    # Pitch mean of (0, 2, -2) = 0
    pitch_range = summary.favored_voice_settings["pitch"]
    assert pitch_range.mean == pytest.approx(0.0, abs=1e-6)

    # "down" settings (speed=2.0, pitch=10.0) must NOT pull the mean.
    assert speed_range.mean < 2.0
    assert pitch_range.mean < 10.0

    # Text characteristics aggregated only from up-rated rows
    assert summary.favored_text.sample_count == 3
    # Texts: "hello world"(11), "hello kind world"(16), "another sample"(14) → avg 13.67
    assert summary.favored_text.avg_char_count == pytest.approx(
        (11 + 16 + 14) / 3, abs=1e-2
    )
    # Word counts: 2, 3, 2 → avg 2.33
    assert summary.favored_text.avg_word_count == pytest.approx(
        (2 + 3 + 2) / 3, abs=1e-2
    )


async def test_aggregate_flattens_nested_voice_settings(db_session: AsyncSession):
    profile = await _make_profile(db_session, name="Nested Pref")

    settings_json = _settings(
        speed=1.0, pitch=0.0,
        voice_settings={"stability": 0.6, "similarity_boost": 0.8},
    )
    h = await _add_history(db_session, profile.id, "nested text", settings_json)
    await _add_feedback(db_session, h.id, "up")

    summary = await aggregate_preferences(db_session, profile.id)

    # Dot-flattened keys
    assert "voice_settings.stability" in summary.favored_voice_settings
    assert summary.favored_voice_settings["voice_settings.stability"].mean == pytest.approx(0.6)
    assert summary.favored_voice_settings["voice_settings.similarity_boost"].mean == pytest.approx(0.8)
    # preset_id is excluded by _IGNORED_SETTINGS_KEYS
    assert "preset_id" not in summary.favored_voice_settings


async def test_summary_to_json_round_trip():
    summary = PreferenceSummary(
        profile_id="p1",
        total_up=5,
        total_down=1,
        favored_voice_settings={"speed": NumericRange(mean=1.0, stdev=0.1, count=5)},
        favored_text=TextCharacteristics(avg_char_count=12.0, avg_word_count=3.0, sample_count=5),
        computed_at=datetime.now(UTC),
    )
    as_json = summary_to_json(summary)
    parsed = json.loads(as_json)
    assert parsed["profile_id"] == "p1"
    assert parsed["total_up"] == 5
    assert parsed["favored_voice_settings"]["speed"]["mean"] == 1.0
    assert parsed["favored_text"]["sample_count"] == 5
    assert parsed["computed_at"] is not None
