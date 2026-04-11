"""Training job model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("voice_profiles.id"), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(50), ForeignKey("providers.name"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued, preprocessing, training, completed, failed, cancelled
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 to 1.0
    celery_task_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON training config
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("model_versions.id"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    profile: Mapped["VoiceProfile"] = relationship("VoiceProfile", back_populates="training_jobs")
