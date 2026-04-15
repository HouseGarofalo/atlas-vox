"""Shared utilities for Celery tasks."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Coroutine
from contextlib import asynccontextmanager
from typing import Any


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run an async coroutine from a sync Celery task context."""
    return asyncio.run(coro)


@asynccontextmanager
async def worker_session() -> AsyncGenerator:
    """Create a fresh async DB session scoped to the current event loop.

    Celery tasks call ``asyncio.run()``, which creates a *new* event loop.
    The module-level engine from ``database.py`` is bound to the loop that
    existed at import time — reusing it causes:

        RuntimeError: Task got Future attached to a different loop

    This helper spins up a throw-away engine + session factory that is
    bound to the *current* loop (the one ``asyncio.run()`` created).
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import settings

    engine = create_async_engine(settings.database_url, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
    await engine.dispose()
