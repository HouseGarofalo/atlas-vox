"""Shared test fixtures.

Each pytest-xdist worker (or standalone run) gets its own SQLite file keyed by
PID, preventing cross-worker collisions.  Tables are created once per process
via a module-scoped asyncio lock.
"""

from __future__ import annotations

import asyncio
import os
import tempfile

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Each worker process gets a unique DB file (safe for pytest-xdist)
_test_db = os.path.join(tempfile.gettempdir(), f"atlas_vox_test_{os.getpid()}.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db}"
os.environ["AUTH_DISABLED"] = "true"
os.environ["DEBUG"] = "false"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-for-unit-tests"

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.models  # noqa: E402, F401
from app.core.database import Base, async_session_factory, engine  # noqa: E402
from app.core.dependencies import get_db  # noqa: E402
from app.main import app  # noqa: E402

_setup_lock = asyncio.Lock()
_tables_created = False


async def _ensure_tables():
    """Create tables and seed providers once per process, guarded by an async lock."""
    global _tables_created
    async with _setup_lock:
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
    """Yield a transactional DB session that rolls back after each test."""
    await _ensure_tables()
    async with async_session_factory() as session:
        # Begin a savepoint so each test's mutations are fully isolated
        async with session.begin_nested():
            yield session
        # Savepoint is automatically rolled back when exiting the context
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """HTTPX async test client wired to the FastAPI app with the test DB session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth helpers — used by test_auth.py and integration tests
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_token():
    """Generate a valid JWT access token for testing."""
    from app.core.security import create_access_token

    return create_access_token(subject="test-user", scopes=["read", "write", "admin"])


@pytest.fixture
def auth_headers(auth_token: str):
    """HTTP headers with a valid Bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}


def pytest_sessionfinish(session, exitstatus):
    """Clean up the per-worker test database file after the session ends."""
    try:
        if os.path.exists(_test_db):
            os.unlink(_test_db)
    except OSError:
        pass
