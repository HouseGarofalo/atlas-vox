"""Shared test fixtures."""

from __future__ import annotations

import os
import tempfile

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Use a temp file DB so all connections (app engine + test sessions) share it
_test_db = os.path.join(tempfile.gettempdir(), "atlas_vox_test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db}"
os.environ["AUTH_DISABLED"] = "true"
os.environ["DEBUG"] = "false"

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.models  # noqa: E402, F401
from app.core.database import Base, async_session_factory, engine  # noqa: E402
from app.core.dependencies import get_db  # noqa: E402
from app.main import app  # noqa: E402

_tables_created = False


async def _ensure_tables():
    global _tables_created
    if _tables_created:
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        from app.models.provider import Provider
        from app.services.provider_registry import PROVIDER_DISPLAY_NAMES, PROVIDER_TYPES

        for name, display in PROVIDER_DISPLAY_NAMES.items():
            session.add(Provider(
                name=name, display_name=display,
                provider_type=PROVIDER_TYPES.get(name, "local"), enabled=True,
            ))
        await session.commit()
    _tables_created = True


@pytest_asyncio.fixture
async def db_session():
    await _ensure_tables()
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
