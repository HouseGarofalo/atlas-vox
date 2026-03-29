"""Self-healing incident log model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    severity: Mapped[str] = mapped_column(
        String(20), index=True
    )  # info, warning, critical
    category: Mapped[str] = mapped_column(
        String(50), index=True
    )  # health, error_rate, latency, queue, provider, resource
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    detection_rule: Mapped[str] = mapped_column(String(100), nullable=True)
    action_taken: Mapped[str] = mapped_column(
        String(100), nullable=True
    )  # none, restart, disable_provider, code_fix, escalate
    action_detail: Mapped[str] = mapped_column(Text, nullable=True)
    outcome: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, resolved, failed, escalated
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
