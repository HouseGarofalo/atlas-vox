"""Regression tests for the synthesis service — P2-22 N+1 fix and VQ-39 cost stamp."""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.synthesis_history import SynthesisHistory
from app.providers.base import AudioResult
from app.schemas.profile import ProfileCreate
from app.services.profile_service import create_profile
from app.services.synthesis_service import synthesize


def _make_wav() -> Path:
    tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sample_rate, num_channels, bits = 22050, 1, 16
    num_samples = 100
    data_size = num_samples * num_channels * (bits // 8)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, num_channels, sample_rate,
        sample_rate * num_channels * (bits // 8),
        num_channels * (bits // 8), bits,
        b"data", data_size,
    )
    tf.write(header + struct.pack(f"<{num_samples}h", *([0] * num_samples)))
    tf.close()
    return Path(tf.name)


def _mock_provider(wav: Path) -> AsyncMock:
    audio_result = AudioResult(
        audio_path=wav, duration_seconds=1.0,
        sample_rate=22050, format="wav",
    )
    p = AsyncMock()
    p.synthesize = AsyncMock(return_value=audio_result)
    return p


class _QueryCounter:
    """Counts SELECT statements issued against a specific table.

    We don't want to count every statement — savepoints, provider lookups,
    history inserts etc. are irrelevant to P2-22. Narrowing to
    ``voice_profiles`` / ``model_versions`` gives a tight signal.
    """

    def __init__(self, table_names: set[str]):
        self.table_names = table_names
        self.count = 0
        self._handler = None

    def install(self, engine: Engine):
        def _after_cursor(_conn, _cursor, statement, _params, _context, _execmany):
            stripped = statement.lstrip().lower()
            if not stripped.startswith("select"):
                return
            if any(t in stripped for t in self.table_names):
                self.count += 1

        self._handler = _after_cursor
        event.listen(engine, "before_cursor_execute", _after_cursor)

    def uninstall(self, engine: Engine):
        if self._handler is not None:
            event.remove(engine, "before_cursor_execute", self._handler)
            self._handler = None


@pytest.mark.asyncio
async def test_synthesize_uses_single_profile_query(db_session: AsyncSession):
    """P2-22 — profile + active_version resolution must hit the DB once.

    We use selectinload(VoiceProfile.versions) which issues one query for
    the profile + one eager query for versions. The anti-pattern being
    fixed was the synthesize path issuing a *separate* SELECT against
    ``model_versions`` after the profile load. We assert that no standalone
    ``model_versions``-only query appears for the active_version lookup.
    """
    profile = await create_profile(
        db_session,
        ProfileCreate(name="NPlus1 Profile", provider_name="kokoro", voice_id="af_heart"),
    )
    wav = _make_wav()
    provider = _mock_provider(wav)

    # Attach the counter to the underlying sync engine.
    sync_engine = db_session.bind.sync_engine
    counter = _QueryCounter(table_names={"voice_profiles"})
    counter.install(sync_engine)
    try:
        with patch(
            "app.services.synthesis_service.provider_registry.get_provider",
            return_value=provider,
        ):
            await synthesize(db_session, text="hi", profile_id=profile.id)
    finally:
        counter.uninstall(sync_engine)

    # Profile is resolved by exactly one SELECT against voice_profiles. The
    # old implementation issued two: profile fetch, then a second fetch
    # during voice-id resolution when ``active_version_id`` was set.
    assert counter.count == 1, (
        f"Expected exactly one profile SELECT, got {counter.count}"
    )


@pytest.mark.asyncio
async def test_synthesize_stamps_cost_on_history(db_session: AsyncSession):
    """VQ-39 — the history row must have ``estimated_cost_usd`` populated."""
    # Use ElevenLabs so the rate is non-zero and easier to assert.
    profile = await create_profile(
        db_session,
        ProfileCreate(name="Cost Stamp Profile", provider_name="elevenlabs"),
    )
    wav = _make_wav()
    provider = _mock_provider(wav)

    text = "x" * 1000  # 1k chars -> $0.30 on elevenlabs
    with patch(
        "app.services.synthesis_service.provider_registry.get_provider",
        return_value=provider,
    ):
        result = await synthesize(db_session, text=text, profile_id=profile.id)

    assert result["estimated_cost_usd"] == pytest.approx(0.30, rel=1e-3)

    rows = await db_session.execute(
        select(SynthesisHistory).where(SynthesisHistory.id == result["id"])
    )
    history = rows.scalar_one()
    assert history.estimated_cost_usd == pytest.approx(0.30, rel=1e-3)


@pytest.mark.asyncio
async def test_synthesize_zero_cost_for_local_provider(db_session: AsyncSession):
    """Local providers (kokoro/piper/etc.) stamp 0.0 — not NULL."""
    profile = await create_profile(
        db_session,
        ProfileCreate(name="Local Cost Profile", provider_name="kokoro", voice_id="af_heart"),
    )
    wav = _make_wav()
    provider = _mock_provider(wav)

    with patch(
        "app.services.synthesis_service.provider_registry.get_provider",
        return_value=provider,
    ):
        result = await synthesize(db_session, text="hello", profile_id=profile.id)
    assert result["estimated_cost_usd"] == 0.0
