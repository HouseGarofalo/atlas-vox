"""Synthesis history log."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SynthesisHistory(Base):
    __tablename__ = "synthesis_history"
    __table_args__ = (
        Index("ix_synthesis_history_profile_created", "profile_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("voice_profiles.id"), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    output_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    output_format: Mapped[str] = mapped_column(String(10), default="wav")
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # speed, pitch, volume, persona
    # STT verification — SL-28. Whisper-computed WER against the original text.
    # Populated asynchronously by ``app.tasks.preferences.verify_synthesis``.
    quality_wer: Mapped[float | None] = mapped_column(Float, nullable=True)
    # VQ-39 — estimated USD cost based on provider per-1k-char rate. NULL for
    # rows written before VQ-39; populated at synthesis time going forward.
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
