"""Synthesis feedback — thumbs up/down ratings on past synthesis outputs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# Valid rating values — enforced at schema layer and service layer.
# Kept as plain strings (not a DB enum) so SQLite-compatible and easy to
# extend with "neutral"/"needs_work" later without a schema migration.
RATING_UP = "up"
RATING_DOWN = "down"
VALID_RATINGS = frozenset({RATING_UP, RATING_DOWN})


class SynthesisFeedback(Base):
    """User rating for a specific synthesis history row.

    A single history row may receive multiple feedback entries (e.g., from
    different users or revisited opinions) — the aggregator treats each row
    independently.
    """

    __tablename__ = "synthesis_feedback"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    history_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("synthesis_history.id"),
        nullable=False,
        index=True,
    )
    rating: Mapped[str] = mapped_column(String(10), nullable=False)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of strings
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )
