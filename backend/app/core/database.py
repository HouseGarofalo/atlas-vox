"""SQLAlchemy async engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = structlog.get_logger(__name__)

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
        cursor = dbapi_conn.cursor()  # type: ignore[union-attr]
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
        logger.info("sqlite_wal_mode_enabled")

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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session, ensuring cleanup."""
    logger.debug("db_session_created")
    async with async_session_factory() as session:
        try:
            yield session
            logger.debug("db_session_commit")
            await session.commit()
        except Exception:
            logger.debug("db_session_rollback")
            await session.rollback()
            raise
        finally:
            logger.debug("db_session_closed")
            await session.close()


async def init_db() -> None:
    """Create all tables (for development/testing). Use Alembic in production."""
    logger.info("db_init_start")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("db_init_complete")
