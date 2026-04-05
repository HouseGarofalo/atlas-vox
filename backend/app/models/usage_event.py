"""Usage tracking for synthesis, cloning, and training operations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    voice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    characters: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    event_type: Mapped[str] = mapped_column(String(20), default="synthesis")  # synthesis, clone, training
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)
