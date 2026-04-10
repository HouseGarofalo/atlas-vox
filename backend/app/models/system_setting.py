"""System settings model — persists configuration to survive container rebuilds."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"
    __table_args__ = (
        UniqueConstraint("category", "key", name="uq_system_settings_category_key"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # general, auth, healing, providers, storage, notifications
    key: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    value: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )  # JSON-encoded; encrypted values prefixed with enc:
    value_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="string"
    )  # string, int, float, bool, json
    is_secret: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    description: Mapped[str] = mapped_column(
        String(500), nullable=False, default=""
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<SystemSetting {self.category}.{self.key}>"
