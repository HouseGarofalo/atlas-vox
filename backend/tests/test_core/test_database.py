"""Tests for app.core.database — init_db and session lifecycle."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, async_session_factory, engine, init_db
from app.core.dependencies import get_db


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_init_db_creates_tables():
    """init_db is idempotent — calling it twice does not raise."""
    # First call (may already have run in conftest, but should be safe)
    await init_db()
    # Second call must not raise
    await init_db()

    # Verify at least one known table exists
    async with engine.connect() as conn:
        # sqlite_master for SQLite
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='voice_profiles'")
        )
        row = result.fetchone()
    assert row is not None, "voice_profiles table was not created by init_db"


@pytest.mark.asyncio
async def test_init_db_creates_all_core_tables():
    """init_db creates all core model tables."""
    await init_db()

    expected_tables = {
        "voice_profiles",
        "model_versions",
        "training_jobs",
        "audio_samples",
        "synthesis_history",
        "providers",
    }
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        existing = {row[0] for row in result.fetchall()}

    missing = expected_tables - existing
    assert not missing, f"Tables missing after init_db: {missing}"


# ---------------------------------------------------------------------------
# get_db session lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_db_yields_session():
    """get_db yields a working AsyncSession."""
    await init_db()
    gen = get_db()
    session = await gen.__anext__()
    try:
        assert isinstance(session, AsyncSession)
        # Execute a trivial query to confirm the session is live
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()
        assert value == 1
    finally:
        # Exhaust the generator to trigger cleanup
        try:
            await gen.aclose()
        except StopAsyncIteration:
            pass


@pytest.mark.asyncio
async def test_get_db_session_from_fixture(db_session: AsyncSession):
    """The db_session fixture provides a usable AsyncSession (integration)."""
    assert isinstance(db_session, AsyncSession)
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
