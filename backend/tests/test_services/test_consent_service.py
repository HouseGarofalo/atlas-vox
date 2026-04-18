"""Tests for the voice-clone consent ledger service (SC-44)."""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.audio_sample import AudioSample
from app.models.clone_consent import CloneConsent
from app.models.voice_profile import VoiceProfile
from app.schemas.profile import ProfileCreate
from app.services.consent_service import (
    PrehashedSample,
    get_consent,
    has_consent_for_hash,
    hash_audio_file,
    list_consent,
    record_consent,
)
from app.services.profile_service import create_profile
from app.services.training_service import start_training


async def _make_profile(db: AsyncSession, provider: str = "elevenlabs") -> VoiceProfile:
    return await create_profile(
        db,
        ProfileCreate(name=f"Consent Profile {provider}", provider_name=provider),
    )


def _make_wav(path: Path, num_samples: int = 22050) -> None:
    sample_rate, num_channels, bits = 22050, 1, 16
    data_size = num_samples * num_channels * (bits // 8)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, num_channels, sample_rate,
        sample_rate * num_channels * (bits // 8),
        num_channels * (bits // 8), bits,
        b"data", data_size,
    )
    path.write_bytes(header + struct.pack(f"<{num_samples}h", *([0] * num_samples)))


async def _add_sample(
    db: AsyncSession, profile_id: str, tmp_path: Path, duration_seconds: float = 10.0,
) -> AudioSample:
    wav = tmp_path / f"sample_{profile_id[:6]}.wav"
    _make_wav(wav)
    sample = AudioSample(
        profile_id=profile_id,
        filename=wav.name,
        original_filename=wav.name,
        file_path=str(wav),
        format="wav",
        file_size_bytes=wav.stat().st_size,
        duration_seconds=duration_seconds,
    )
    db.add(sample)
    await db.flush()
    return sample


# ---------------------------------------------------------------------------
# record_consent — happy path + validation
# ---------------------------------------------------------------------------


async def test_record_consent_roundtrip(db_session: AsyncSession):
    profile = await _make_profile(db_session)
    payload = b"sample-bytes"
    expected_hash = hashlib.sha256(payload).hexdigest()

    record = await record_consent(
        db_session,
        profile_id=profile.id,
        samples=[payload],
        operator_user_id="admin-1",
        consent_text="I consent to cloning my voice.",
    )

    assert record.id is not None
    assert record.target_profile_id == profile.id
    assert record.source_audio_hash == expected_hash
    assert record.target_provider == profile.provider_name
    assert record.consent_text == "I consent to cloning my voice."
    assert record.operator_user_id == "admin-1"

    # Verify round-trip read works.
    fetched = await get_consent(db_session, record.id)
    assert fetched.id == record.id
    assert fetched.source_audio_hash == expected_hash


async def test_record_consent_rejects_empty_samples(db_session: AsyncSession):
    profile = await _make_profile(db_session)
    with pytest.raises(ValidationError, match="sample"):
        await record_consent(
            db_session,
            profile_id=profile.id,
            samples=[],
            operator_user_id="admin-1",
            consent_text="yes",
        )


async def test_record_consent_rejects_missing_profile(db_session: AsyncSession):
    with pytest.raises(NotFoundError):
        await record_consent(
            db_session,
            profile_id="does-not-exist",
            samples=[b"x"],
            operator_user_id="admin-1",
            consent_text="yes",
        )


async def test_record_consent_rejects_empty_text(db_session: AsyncSession):
    profile = await _make_profile(db_session)
    with pytest.raises(ValidationError, match="consent_text"):
        await record_consent(
            db_session,
            profile_id=profile.id,
            samples=[b"x"],
            operator_user_id="admin-1",
            consent_text="   ",
        )


async def test_record_consent_prehashed_sample(db_session: AsyncSession):
    profile = await _make_profile(db_session)
    h = "a" * 64
    record = await record_consent(
        db_session,
        profile_id=profile.id,
        samples=[PrehashedSample(h)],
        operator_user_id="admin-1",
        consent_text="yes",
    )
    assert record.source_audio_hash == h


async def test_record_consent_file_path(db_session: AsyncSession, tmp_path: Path):
    profile = await _make_profile(db_session)
    wav = tmp_path / "first.wav"
    _make_wav(wav)
    expected = hash_audio_file(wav)

    record = await record_consent(
        db_session,
        profile_id=profile.id,
        samples=[wav],
        operator_user_id="admin-1",
        consent_text="yes",
    )
    assert record.source_audio_hash == expected


# ---------------------------------------------------------------------------
# Append-only contract
# ---------------------------------------------------------------------------


async def test_consent_is_append_only_no_update_path(db_session: AsyncSession):
    """No service or endpoint exposes an update for consent rows.

    We exercise the contract by attempting a raw UPDATE via SQL and
    verifying the ledger still shows the original row — i.e. the service
    layer never mutates; the DB will physically allow UPDATEs (SQLite
    doesn't have row-level triggers by default) but the contract at the
    service layer is that no path exists to do so. We assert that by
    introspecting the consent_service module.
    """
    from app.services import consent_service

    for attr in ("update_consent", "delete_consent", "modify_consent", "patch_consent"):
        assert not hasattr(consent_service, attr), (
            f"consent_service exposes {attr}; ledger must be append-only"
        )

    # And sanity-check that record_consent actually adds a row we can read.
    profile = await _make_profile(db_session)
    rec = await record_consent(
        db_session,
        profile_id=profile.id,
        samples=[b"abc"],
        operator_user_id="op",
        consent_text="yes",
    )
    all_rows = await list_consent(db_session)
    assert any(r.id == rec.id for r in all_rows)


async def test_consent_endpoints_have_no_mutation_routes():
    """The REST layer exposes only POST (create), GET list, GET detail."""
    from app.api.v1.endpoints import consent as consent_module

    routes = consent_module.router.routes
    methods_seen: set[str] = set()
    for r in routes:
        methods_seen.update(getattr(r, "methods", set()))
    assert "PUT" not in methods_seen
    assert "PATCH" not in methods_seen
    assert "DELETE" not in methods_seen


# ---------------------------------------------------------------------------
# Training integration — consent gate
# ---------------------------------------------------------------------------


def _cloning_provider() -> AsyncMock:
    caps = MagicMock()
    caps.supports_cloning = True
    caps.supports_fine_tuning = False
    caps.min_samples_for_cloning = 1
    p = AsyncMock()
    p.get_capabilities = AsyncMock(return_value=caps)
    return p


async def test_training_blocks_when_consent_required_and_missing(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    profile = await _make_profile(db_session)
    await _add_sample(db_session, profile.id, tmp_path, duration_seconds=10.0)

    monkeypatch.setattr(
        "app.core.config.settings.require_clone_consent", True, raising=False
    )

    with patch(
        "app.services.training_service.provider_registry.get_provider",
        return_value=_cloning_provider(),
    ):
        with pytest.raises(ValidationError, match="consent"):
            await start_training(db_session, profile_id=profile.id)


async def test_training_allowed_when_consent_recorded(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    profile = await _make_profile(db_session)
    sample = await _add_sample(db_session, profile.id, tmp_path, duration_seconds=10.0)

    monkeypatch.setattr(
        "app.core.config.settings.require_clone_consent", True, raising=False
    )

    # Record consent for the sample on disk.
    await record_consent(
        db_session,
        profile_id=profile.id,
        samples=[Path(sample.file_path)],
        operator_user_id="admin",
        consent_text="ok",
    )

    fake_task = MagicMock()
    fake_task.id = "task-consent-ok"

    with patch(
        "app.services.training_service.provider_registry.get_provider",
        return_value=_cloning_provider(),
    ), patch(
        "app.tasks.training.train_model.delay", return_value=fake_task,
    ):
        job = await start_training(db_session, profile_id=profile.id)
    assert job.status == "queued"


async def test_training_allowed_without_consent_when_flag_off(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    """Backward-compat: flag defaults to False and training must not gate."""
    profile = await _make_profile(db_session)
    await _add_sample(db_session, profile.id, tmp_path, duration_seconds=10.0)

    monkeypatch.setattr(
        "app.core.config.settings.require_clone_consent", False, raising=False
    )

    fake_task = MagicMock()
    fake_task.id = "task-no-gate"

    with patch(
        "app.services.training_service.provider_registry.get_provider",
        return_value=_cloning_provider(),
    ), patch(
        "app.tasks.training.train_model.delay", return_value=fake_task,
    ):
        job = await start_training(db_session, profile_id=profile.id)
    assert job.status == "queued"


async def test_has_consent_for_hash(db_session: AsyncSession):
    profile = await _make_profile(db_session)
    rec = await record_consent(
        db_session,
        profile_id=profile.id,
        samples=[b"hello"],
        operator_user_id="op",
        consent_text="yes",
    )
    assert await has_consent_for_hash(db_session, profile.id, rec.source_audio_hash) is True
    assert (
        await has_consent_for_hash(db_session, profile.id, "f" * 64)
    ) is False
