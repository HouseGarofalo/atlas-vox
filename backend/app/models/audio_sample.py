"""Audio sample model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AudioSample(Base):
    __tablename__ = "audio_samples"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("voice_profiles.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)  # wav, mp3, flac, etc.
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preprocessed: Mapped[bool] = mapped_column(default=False)
    preprocessed_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    analysis_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: pitch, energy, spectral
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    profile: Mapped[VoiceProfile] = relationship("VoiceProfile", back_populates="samples")


from app.models.voice_profile import VoiceProfile  # noqa: E402
