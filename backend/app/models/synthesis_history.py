"""Synthesis history log."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SynthesisHistory(Base):
    __tablename__ = "synthesis_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(String(36), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    output_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    output_format: Mapped[str] = mapped_column(String(10), default="wav")
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # speed, pitch, volume, persona
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
