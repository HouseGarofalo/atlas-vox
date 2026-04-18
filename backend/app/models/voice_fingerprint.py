"""Voice fingerprint model — stores speaker embeddings per uploaded sample.

Embeddings are produced by ``app.services.voice_fingerprinter.compute_fingerprint``
and serialised as JSON in the ``embedding_json`` column.  The ``method``
column records which embedding algorithm produced the vector
(e.g. ``resemblyzer``, ``mfcc_mean``), making it possible to reason about
cross-method comparisons.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VoiceFingerprint(Base):
    __tablename__ = "voice_fingerprints"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    sample_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("audio_samples.id"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("voice_profiles.id"),
        nullable=False,
        index=True,
    )
    embedding_json: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False, default="mfcc_mean")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
