"""Persona preset model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PersonaPreset(Base):
    __tablename__ = "persona_presets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    speed: Mapped[float] = mapped_column(Float, default=1.0)  # 0.5 to 2.0
    pitch: Mapped[float] = mapped_column(Float, default=0.0)  # -50 to +50
    volume: Mapped[float] = mapped_column(Float, default=1.0)  # 0.0 to 2.0
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # True for built-in presets
    settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # Extra provider-specific settings
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
