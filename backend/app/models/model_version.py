"""Trained model version."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("voice_profiles.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_model_id: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Provider-specific ID
    model_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # Local model file path
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # Training config snapshot
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # Quality metrics
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    profile: Mapped[VoiceProfile] = relationship(
        "VoiceProfile",
        back_populates="versions",
        foreign_keys=[profile_id],
    )


from app.models.voice_profile import VoiceProfile  # noqa: E402
