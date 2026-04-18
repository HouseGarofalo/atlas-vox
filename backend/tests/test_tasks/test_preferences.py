"""Tests for SL-26 rollup + SL-28 verify Celery tasks."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preference_summary import PreferenceSummary as PreferenceSummaryModel
from app.models.synthesis_feedback import SynthesisFeedback
from app.models.synthesis_history import SynthesisHistory
from app.schemas.profile import ProfileCreate
from app.services.profile_service import create_profile
from app.tasks import preferences as prefs_task
from app.tasks.preferences import (
    QUALITY_WER_FLAG_THRESHOLD,
    _rollup_preferences_async,
    _verify_synthesis_async,
    compute_wer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_profile(db: AsyncSession, name: str):
    return await create_profile(
        db,
        ProfileCreate(name=name, provider_name="kokoro", voice_id="af_heart"),
    )


def _patch_worker_session(db_session: AsyncSession):
    """Return a patcher that redirects ``worker_session`` to the test session.

    The test session uses a transactional savepoint so we must avoid the
    real ``commit()`` the task performs (it would close the savepoint).  We
    substitute ``commit`` with ``flush`` for the duration of the task.
    """

    class _Wrapper:
        def __init__(self, sess: AsyncSession):
            self._sess = sess

        def __getattr__(self, item):
            return getattr(self._sess, item)

        async def commit(self):  # pragma: no cover - trivial
            await self._sess.flush()

    @asynccontextmanager
    async def _fake_worker_session():
        yield _Wrapper(db_session)

    return _fake_worker_session


# ---------------------------------------------------------------------------
# SL-26 — rollup_preferences end-to-end
# ---------------------------------------------------------------------------

async def test_rollup_preferences_writes_summary_rows(db_session: AsyncSession):
    profile = await _make_profile(db_session, name="Rollup Test")

    hist = SynthesisHistory(
        profile_id=profile.id,
        provider_name="kokoro",
        text="hello world",
        output_path="/tmp/fake.wav",
        output_format="wav",
        duration_seconds=1.0,
        latency_ms=10,
        settings_json=json.dumps({"speed": 1.1, "pitch": 0.0, "volume": 1.0}),
    )
    db_session.add(hist)
    await db_session.flush()
    db_session.add(SynthesisFeedback(history_id=hist.id, rating="up"))
    await db_session.flush()

    fake_ws = _patch_worker_session(db_session)
    with patch("app.tasks.preferences.worker_session", fake_ws):
        result = await _rollup_preferences_async()

    assert result["profiles_updated"] == 1

    # A PreferenceSummary row now exists for our profile with the expected JSON shape.
    summary_row = (
        await db_session.execute(
            select(PreferenceSummaryModel).where(
                PreferenceSummaryModel.profile_id == profile.id
            )
        )
    ).scalar_one()
    payload = json.loads(summary_row.summary_json)
    assert payload["profile_id"] == profile.id
    assert payload["total_up"] == 1
    assert payload["total_down"] == 0
    assert payload["favored_voice_settings"]["speed"]["count"] == 1


async def test_rollup_preferences_ignores_profiles_without_feedback(
    db_session: AsyncSession,
):
    await _make_profile(db_session, name="Lonely Profile")

    fake_ws = _patch_worker_session(db_session)
    with patch("app.tasks.preferences.worker_session", fake_ws):
        result = await _rollup_preferences_async()

    assert result["profiles_updated"] == 0


# ---------------------------------------------------------------------------
# Celery task registration (no broker required)
# ---------------------------------------------------------------------------

def test_rollup_preferences_registered_as_celery_task():
    from app.tasks.preferences import rollup_preferences

    assert hasattr(rollup_preferences, "delay")
    assert rollup_preferences.name == "app.tasks.preferences.rollup_preferences"


def test_verify_synthesis_registered_as_celery_task():
    from app.tasks.preferences import verify_synthesis

    assert hasattr(verify_synthesis, "delay")
    assert verify_synthesis.name == "app.tasks.preferences.verify_synthesis"


def test_beat_schedule_includes_nightly_rollup():
    from app.tasks.celery_app import celery_app

    beat = celery_app.conf.beat_schedule
    assert "rollup-preferences-nightly" in beat
    assert beat["rollup-preferences-nightly"]["task"] == "app.tasks.preferences.rollup_preferences"


# ---------------------------------------------------------------------------
# SL-28 — WER + verify_synthesis
# ---------------------------------------------------------------------------

def test_compute_wer_exact_match_is_zero():
    assert compute_wer("hello world", "hello world") == 0.0


def test_compute_wer_case_and_punctuation_insensitive():
    assert compute_wer("Hello, World!", "hello world") == 0.0


def test_compute_wer_substitutions():
    # "hello world" vs. "hello globe" → 1 substitution / 2 words
    assert compute_wer("hello world", "hello globe") == pytest.approx(0.5)


def test_compute_wer_empty_hypothesis_is_one():
    assert compute_wer("hello world", "") == 1.0


def test_compute_wer_empty_reference_is_zero():
    assert compute_wer("", "anything at all") == 0.0


async def test_verify_synthesis_writes_wer_to_row(db_session: AsyncSession, tmp_path: Path):
    profile = await _make_profile(db_session, name="Verify Test")

    audio_path = tmp_path / "out.wav"
    audio_path.write_bytes(b"pretend this is wav")

    hist = SynthesisHistory(
        profile_id=profile.id,
        provider_name="kokoro",
        text="the quick brown fox",
        output_path=str(audio_path),
        output_format="wav",
        duration_seconds=1.0,
        latency_ms=10,
    )
    db_session.add(hist)
    await db_session.flush()

    fake_ws = _patch_worker_session(db_session)
    with patch("app.tasks.preferences.worker_session", fake_ws), patch(
        "app.services.whisper_transcriber.transcribe",
        new=AsyncMock(return_value="the quick brown dog"),
    ):
        result = await _verify_synthesis_async(hist.id)

    # 1 substitution over 4 ref words = 0.25
    assert result["wer"] == pytest.approx(0.25)
    await db_session.refresh(hist)
    assert hist.quality_wer == pytest.approx(0.25)


async def test_verify_synthesis_skips_missing_audio(db_session: AsyncSession, tmp_path: Path):
    profile = await _make_profile(db_session, name="Missing Audio")

    hist = SynthesisHistory(
        profile_id=profile.id,
        provider_name="kokoro",
        text="hello world",
        output_path=str(tmp_path / "never_existed.wav"),
        output_format="wav",
        duration_seconds=1.0,
        latency_ms=10,
    )
    db_session.add(hist)
    await db_session.flush()

    fake_ws = _patch_worker_session(db_session)
    with patch("app.tasks.preferences.worker_session", fake_ws):
        result = await _verify_synthesis_async(hist.id)

    assert result["skipped"] == "audio_missing"
    await db_session.refresh(hist)
    assert hist.quality_wer is None


async def test_verify_synthesis_unknown_history(db_session: AsyncSession):
    fake_ws = _patch_worker_session(db_session)
    with patch("app.tasks.preferences.worker_session", fake_ws):
        result = await _verify_synthesis_async("does-not-exist")

    assert result["skipped"] == "missing"


# Sanity check that the flag threshold is sensible.
def test_quality_wer_flag_threshold_in_range():
    assert 0.0 < QUALITY_WER_FLAG_THRESHOLD < 1.0
