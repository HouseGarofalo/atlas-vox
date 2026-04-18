"""Voice clone consent ledger — append-only audit trail.

Every voice-cloning operation should have a corresponding ``CloneConsent``
row that records the operator who granted consent, the target profile, the
exact consent text shown to the user, and a sha256 hash of the source audio
so that the exact sample used for cloning can be identified after the fact.

The ledger is append-only by convention: there are no update or delete
endpoints that expose these rows to callers.  Rows may only be created via
the ``POST /api/v1/consent`` endpoint or the service function
``consent_service.record_consent``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CloneConsent(Base):
    """Append-only consent record for voice cloning.

    Columns:

    - ``source_audio_hash`` — sha256 of the first sample's bytes, hex-encoded.
    - ``target_profile_id`` — the profile the cloned voice will belong to.
    - ``target_provider`` — the provider name (e.g. ``elevenlabs``) used for
      the clone operation.  String (not FK) so the record survives provider
      renames / removals.
    - ``consent_text`` — the exact consent string shown to / acknowledged by
      the operator at the time of grant.
    - ``consent_granted_at`` — UTC timestamp at grant time.
    - ``operator_user_id`` — identifier of the operator who granted consent
      (e.g. JWT sub claim or API-key id).  String to accommodate any
      identity scheme.
    - ``consent_proof_blob`` — optional reference to a proof artifact (e.g.
      a URL pointing at an uploaded consent-recording, or a digital
      signature).  Free-form text.
    """

    __tablename__ = "clone_consent"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_audio_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("voice_profiles.id"),
        nullable=False,
        index=True,
    )
    target_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    consent_text: Mapped[str] = mapped_column(Text, nullable=False)
    consent_granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    operator_user_id: Mapped[str] = mapped_column(String(200), nullable=False)
    consent_proof_blob: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
