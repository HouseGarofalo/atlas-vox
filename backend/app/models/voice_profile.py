"""Voice profile model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.audio_sample import AudioSample
    from app.models.model_version import ModelVersion
    from app.models.training_job import TrainingJob


class VoiceProfile(Base):
    __tablename__ = "voice_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    provider_name: Mapped[str] = mapped_column(String(50), ForeignKey("providers.name"), nullable=False)
    voice_id: Mapped[str | None] = mapped_column(String(200), nullable=True)  # Pre-built voice ID (e.g., "af_heart", "en-US-JennyNeural")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, training, ready, error, archived
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of strings
    active_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("model_versions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    samples: Mapped[list[AudioSample]] = relationship("AudioSample", back_populates="profile", cascade="all, delete-orphan")
    versions: Mapped[list[ModelVersion]] = relationship(
        "ModelVersion",
        back_populates="profile",
        foreign_keys="ModelVersion.profile_id",
        cascade="all, delete-orphan",
    )
    training_jobs: Mapped[list[TrainingJob]] = relationship("TrainingJob", back_populates="profile", cascade="all, delete-orphan")
