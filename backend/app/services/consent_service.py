"""Voice clone consent ledger — service layer (SC-44).

Recording consent is intentionally a small, explicit operation that services
and endpoints call before invoking any provider's ``clone_voice()``.  The
ledger is append-only — there is no update or delete API, and callers should
not mutate existing rows.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.clone_consent import CloneConsent
from app.models.voice_profile import VoiceProfile
from app.providers.base import ProviderAudioSample

logger = structlog.get_logger(__name__)


def _hash_bytes(data: bytes) -> str:
    """Return hex sha256 of the given bytes."""
    return hashlib.sha256(data).hexdigest()


def hash_audio_file(path: Path) -> str:
    """Compute sha256 hex digest of an audio file on disk.

    Reads the file in chunks so large WAVs don't blow memory.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class PrehashedSample:
    """A sample represented purely by its sha256 hex digest.

    Useful when the caller already has a trusted hash (e.g. from a previous
    upload step) and doesn't want to re-read the audio bytes.
    """

    __slots__ = ("hash_hex",)

    def __init__(self, hash_hex: str) -> None:
        if not isinstance(hash_hex, str) or len(hash_hex) != 64:
            raise ValidationError("Pre-hashed sample must be a 64-char hex digest")
        self.hash_hex = hash_hex.lower()


def _sample_hash(sample) -> str:
    """Coerce the supported sample shapes into a sha256 hex digest."""
    if isinstance(sample, PrehashedSample):
        return sample.hash_hex
    if isinstance(sample, bytes):
        return _hash_bytes(sample)
    if isinstance(sample, ProviderAudioSample):
        return hash_audio_file(Path(sample.file_path))
    if isinstance(sample, (str, Path)):
        return hash_audio_file(Path(sample))
    raise ValidationError(
        f"Unsupported sample type for consent hashing: {type(sample).__name__}"
    )


async def record_consent(
    db: AsyncSession,
    profile_id: str,
    samples: list,
    operator_user_id: str,
    consent_text: str,
    target_provider: str | None = None,
    consent_proof_blob: str | None = None,
) -> CloneConsent:
    """Record a voice-clone consent entry.

    ``samples`` may contain ``ProviderAudioSample`` instances, raw ``bytes``
    objects, or ``pathlib.Path`` / str file paths — whichever is most
    convenient at the call site.  The hash is computed over the *first*
    entry in the list (deterministic and cheap).
    """
    if not samples:
        raise ValidationError("At least one sample is required to record consent")
    if not consent_text or not consent_text.strip():
        raise ValidationError("consent_text is required and must be non-empty")
    if not operator_user_id:
        raise ValidationError("operator_user_id is required")

    result = await db.execute(
        select(VoiceProfile).where(VoiceProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise NotFoundError("Profile", profile_id)

    source_hash = _sample_hash(samples[0])
    provider = target_provider or profile.provider_name

    record = CloneConsent(
        source_audio_hash=source_hash,
        target_profile_id=profile_id,
        target_provider=provider,
        consent_text=consent_text.strip(),
        operator_user_id=operator_user_id,
        consent_proof_blob=consent_proof_blob,
    )
    db.add(record)
    await db.flush()

    logger.info(
        "clone_consent_recorded",
        consent_id=record.id,
        profile_id=profile_id,
        provider=provider,
        operator=operator_user_id,
        source_audio_hash=source_hash,
    )
    return record


async def has_consent_for_hash(
    db: AsyncSession, profile_id: str, source_audio_hash: str
) -> bool:
    """Return True iff a consent row exists for (profile_id, source_audio_hash)."""
    result = await db.execute(
        select(CloneConsent.id).where(
            CloneConsent.target_profile_id == profile_id,
            CloneConsent.source_audio_hash == source_audio_hash,
        )
    )
    return result.scalar_one_or_none() is not None


async def list_consent(
    db: AsyncSession,
    profile_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[CloneConsent]:
    """List consent records with optional profile filter and pagination."""
    query = select(CloneConsent).order_by(CloneConsent.consent_granted_at.desc())
    if profile_id:
        query = query.where(CloneConsent.target_profile_id == profile_id)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_consent(db: AsyncSession, consent_id: str) -> CloneConsent:
    """Return a single consent row by id, raising NotFoundError if missing."""
    result = await db.execute(
        select(CloneConsent).where(CloneConsent.id == consent_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise NotFoundError("CloneConsent", consent_id)
    return record
