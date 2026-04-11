"""SQLAlchemy async engine and session factory."""

from __future__ import annotations

import structlog
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Module-level flag to ensure WAL mode is only logged on first connection
_wal_mode_logged = False

connect_args = {}
if settings.is_sqlite:
    connect_args["check_same_thread"] = False

if settings.is_sqlite:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug and not settings.is_production,
        connect_args=connect_args,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_wal_mode(dbapi_conn: object, connection_record: object) -> None:
        """Enable WAL journal mode for better concurrent read performance."""
        global _wal_mode_logged
        cursor = dbapi_conn.cursor()  # type: ignore[union-attr]
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
        if not _wal_mode_logged:
            logger.info("sqlite_wal_mode_enabled")
            _wal_mode_logged = True

else:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug and not settings.is_production,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass





async def init_db() -> None:
    """Create all tables (development/testing convenience).

    For production deployments, use Alembic migrations instead:
        alembic upgrade head
    """
    logger.info("db_init_start")
    async with engine.begin() as conn:
        # create_all is idempotent — safe for dev/test but production should use Alembic
        await conn.run_sync(Base.metadata.create_all)

    # Schema migrations are handled by Alembic. Run: alembic upgrade head
    logger.info("db_init_complete")
