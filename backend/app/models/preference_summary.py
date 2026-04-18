"""Per-profile preference summary — rolled up from SynthesisFeedback nightly."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PreferenceSummary(Base):
    """Nightly-refreshed rollup of preferences for one voice profile.

    ``summary_json`` stores the serialised ``PreferenceSummary`` dataclass
    produced by ``app.services.preference_aggregator``.  Exactly one row per
    profile — the ``rollup_preferences`` task upserts.
    """

    __tablename__ = "preference_summaries"

    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("voice_profiles.id"),
        primary_key=True,
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
