"""P0-07: Verify ModelVersion rows get created and surfaced end-to-end.

These tests don't run the full Celery worker — they exercise the
``_create_version`` helper directly (the part that actually writes the
row) and then drive ``list_versions`` + the ``version_count`` subquery
that powers the UI.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_sample import AudioSample
from app.models.model_version import ModelVersion
from app.models.training_job import TrainingJob
from app.models.voice_profile import VoiceProfile
from app.providers.base import VoiceModel
from app.schemas.profile import ProfileCreate
from app.services.profile_service import create_profile, list_profiles
from app.services.training_service import list_versions
from app.tasks.training import _create_version


async def _make_profile(db: AsyncSession, name: str = "T") -> VoiceProfile:
    return await create_profile(
        db, ProfileCreate(name=name, provider_name="elevenlabs", voice_id="")
    )


async def _make_job(db: AsyncSession, profile_id: str) -> TrainingJob:
    job = TrainingJob(
        profile_id=profile_id,
        provider_name="elevenlabs",
        status="training",
        progress=0.5,
        config_json=json.dumps({"epochs": 10}),
    )
    db.add(job)
    await db.flush()
    return job


def _make_voice_model(idx: int) -> VoiceModel:
    """Build a VoiceModel as a provider would return on successful train."""
    return VoiceModel(
        model_id=f"model-{idx}",
        model_path=Path(f"/tmp/model-{idx}.bin"),
        provider_model_id=f"avx_{idx:04d}",
        metrics={"method": "clone", "duration_s": 12.5 + idx, "quality_wer": 0.05 + 0.01 * idx},
    )


@pytest.fixture
def fake_task():
    t = AsyncMock()
    t.update_state = AsyncMock()
    return t


@pytest.fixture
def transactional_db_session(db_session: AsyncSession, monkeypatch):
    """Let tests call production code that does ``await db.commit()`` without
    closing the conftest's nested savepoint.

    The outer conftest fixture wraps each test in a ``begin_nested()`` so it
    can roll back; but ``_create_version`` commits — which on a SQLite
    savepoint ends the outer context. We patch commit() to flush instead,
    which is functionally equivalent for our assertions and keeps the
    savepoint alive until rollback.
    """
    orig_commit = db_session.commit

    async def flush_only():
        # Flush so rows are written but the savepoint transaction stays open.
        await db_session.flush()

    monkeypatch.setattr(db_session, "commit", flush_only)
    yield db_session
    # Restore for completeness (rollback in conftest will still clean up).
    monkeypatch.setattr(db_session, "commit", orig_commit)


class TestCreateVersion:
    async def test_first_version_is_numbered_1(
        self, transactional_db_session: AsyncSession, fake_task
    ):
        profile = await _make_profile(transactional_db_session)
        job = await _make_job(transactional_db_session, profile.id)
        version, n = await _create_version(transactional_db_session, job, _make_voice_model(1), fake_task, job.id)
        assert n == 1
        assert version.version_number == 1
        assert version.profile_id == profile.id
        assert version.provider_model_id == "avx_0001"

    async def test_second_version_increments_to_2(
        self, transactional_db_session: AsyncSession, fake_task
    ):
        profile = await _make_profile(transactional_db_session)
        j1 = await _make_job(transactional_db_session, profile.id)
        await _create_version(transactional_db_session, j1, _make_voice_model(1), fake_task, j1.id)
        j2 = await _make_job(transactional_db_session, profile.id)
        _, n = await _create_version(transactional_db_session, j2, _make_voice_model(2), fake_task, j2.id)
        assert n == 2

    async def test_profile_becomes_ready_after_first_version(
        self, transactional_db_session: AsyncSession, fake_task
    ):
        profile = await _make_profile(transactional_db_session)
        job = await _make_job(transactional_db_session, profile.id)
        version, _ = await _create_version(transactional_db_session, job, _make_voice_model(1), fake_task, job.id)

        refreshed = (await transactional_db_session.execute(
            select(VoiceProfile).where(VoiceProfile.id == profile.id)
        )).scalar_one()
        assert refreshed.status == "ready"
        assert refreshed.active_version_id == version.id

    async def test_metrics_persisted_as_json(
        self, transactional_db_session: AsyncSession, fake_task
    ):
        profile = await _make_profile(transactional_db_session)
        job = await _make_job(transactional_db_session, profile.id)
        version, _ = await _create_version(transactional_db_session, job, _make_voice_model(7), fake_task, job.id)

        parsed = json.loads(version.metrics_json)
        assert parsed["method"] == "clone"
        assert parsed["duration_s"] == pytest.approx(19.5)
        assert parsed["quality_wer"] == pytest.approx(0.12)

    async def test_training_job_links_to_version(
        self, transactional_db_session: AsyncSession, fake_task
    ):
        profile = await _make_profile(transactional_db_session)
        job = await _make_job(transactional_db_session, profile.id)
        version, _ = await _create_version(transactional_db_session, job, _make_voice_model(1), fake_task, job.id)
        assert job.result_version_id == version.id
        assert job.status == "completed"


class TestListVersions:
    async def test_list_returns_all_versions_for_profile(
        self, transactional_db_session: AsyncSession, fake_task
    ):
        profile = await _make_profile(transactional_db_session)
        for i in range(3):
            job = await _make_job(transactional_db_session, profile.id)
            await _create_version(transactional_db_session, job, _make_voice_model(i + 1), fake_task, job.id)

        versions = await list_versions(transactional_db_session, profile_id=profile.id)
        assert len(versions) == 3
        # list_versions returns newest-first.
        assert [v.version_number for v in versions] == [3, 2, 1]

    async def test_list_empty_profile_returns_empty(
        self, transactional_db_session: AsyncSession
    ):
        profile = await _make_profile(transactional_db_session)
        versions = await list_versions(transactional_db_session, profile_id=profile.id)
        assert versions == []


class TestVersionCountSubquery:
    async def test_profile_list_version_count_matches_created_versions(
        self, transactional_db_session: AsyncSession, fake_task
    ):
        profile = await _make_profile(transactional_db_session, name="Counted")
        # Create 2 versions.
        for i in range(2):
            job = await _make_job(transactional_db_session, profile.id)
            await _create_version(transactional_db_session, job, _make_voice_model(i + 1), fake_task, job.id)

        from app.services.profile_service import list_profiles_with_counts
        rows = await list_profiles_with_counts(transactional_db_session)
        match = next(r for r in rows if r["profile"].id == profile.id)
        assert match["version_count"] == 2

    async def test_profile_list_version_count_zero_when_untrained(
        self, transactional_db_session: AsyncSession
    ):
        profile = await _make_profile(transactional_db_session, name="Untrained")
        from app.services.profile_service import list_profiles_with_counts
        rows = await list_profiles_with_counts(transactional_db_session)
        match = next(r for r in rows if r["profile"].id == profile.id)
        assert match["version_count"] == 0


class TestActivateVersion:
    async def test_promoting_older_version_flips_active_id(
        self, transactional_db_session: AsyncSession, fake_task
    ):
        from app.services.training_service import activate_version

        profile = await _make_profile(transactional_db_session)
        j1 = await _make_job(transactional_db_session, profile.id)
        v1, _ = await _create_version(transactional_db_session, j1, _make_voice_model(1), fake_task, j1.id)
        j2 = await _make_job(transactional_db_session, profile.id)
        v2, _ = await _create_version(transactional_db_session, j2, _make_voice_model(2), fake_task, j2.id)
        # After two trainings, v2 should be active (newest wins).
        refreshed = (await transactional_db_session.execute(
            select(VoiceProfile).where(VoiceProfile.id == profile.id)
        )).scalar_one()
        assert refreshed.active_version_id == v2.id

        # Promote v1.
        await activate_version(transactional_db_session, profile_id=profile.id, version_id=v1.id)
        refreshed = (await transactional_db_session.execute(
            select(VoiceProfile).where(VoiceProfile.id == profile.id)
        )).scalar_one()
        assert refreshed.active_version_id == v1.id
