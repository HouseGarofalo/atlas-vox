"""Voice fingerprinting service (SC-46).

Produces a compact speaker embedding for an audio file.  The service tries
resemblyzer first (if installed) and falls back to an MFCC-mean embedding
via librosa for the v1 implementation.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import numpy as np
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.voice_fingerprint import VoiceFingerprint
from app.models.voice_profile import VoiceProfile

logger = structlog.get_logger(__name__)


_METHOD_RESEMBLYZER = "resemblyzer"
_METHOD_MFCC = "mfcc_mean"


def _try_resemblyzer(audio_path: Path) -> list[float] | None:
    """Use resemblyzer's ``VoiceEncoder`` if available, else return None."""
    try:
        from resemblyzer import VoiceEncoder, preprocess_wav  # type: ignore
    except Exception:
        return None

    try:
        wav = preprocess_wav(str(audio_path))
        encoder = VoiceEncoder()
        embedding = encoder.embed_utterance(wav)
        return np.asarray(embedding, dtype=np.float32).tolist()
    except Exception as exc:  # pragma: no cover - optional dependency path
        logger.warning("resemblyzer_failed", path=str(audio_path), error=str(exc))
        return None


def _mfcc_mean_embedding(audio_path: Path) -> list[float]:
    """Compute a 40-dim MFCC mean embedding via librosa."""
    import librosa  # lazy import

    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    if y.size == 0:
        raise ValueError("Audio file is empty or unreadable")
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
    embedding = mfcc.mean(axis=1)
    # L2-normalize so cosine similarity behaves nicely.
    norm = float(np.linalg.norm(embedding))
    if norm > 0:
        embedding = embedding / norm
    return np.asarray(embedding, dtype=np.float32).tolist()


def _compute_sync(audio_path: Path) -> tuple[list[float], str]:
    """Blocking implementation — runs in a thread via ``run_sync``."""
    embedding = _try_resemblyzer(audio_path)
    if embedding is not None:
        return embedding, _METHOD_RESEMBLYZER
    return _mfcc_mean_embedding(audio_path), _METHOD_MFCC


async def compute_fingerprint(audio_path: Path) -> list[float]:
    """Return an embedding vector for the given audio file.

    The compute is I/O- and CPU-heavy, so it's dispatched to a thread pool
    to avoid blocking the event loop.
    """
    path = Path(audio_path)
    embedding, method = await asyncio.get_running_loop().run_in_executor(
        None, _compute_sync, path
    )
    logger.info(
        "fingerprint_computed",
        path=str(path),
        method=method,
        dims=len(embedding),
    )
    return embedding


async def compute_fingerprint_with_method(audio_path: Path) -> tuple[list[float], str]:
    """Return both the embedding and the method label used to produce it."""
    path = Path(audio_path)
    embedding, method = await asyncio.get_running_loop().run_in_executor(
        None, _compute_sync, path
    )
    return embedding, method


def cosine_similarity(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    """Cosine similarity between two equal-length vectors.

    Returns 0.0 if either vector is the zero vector or has mismatching
    dimensionality — the latter is a degenerate case we don't want to
    raise for in the cross-profile matching endpoint.
    """
    av = np.asarray(a, dtype=np.float32)
    bv = np.asarray(b, dtype=np.float32)
    if av.shape != bv.shape or av.size == 0:
        return 0.0
    na = float(np.linalg.norm(av))
    nb = float(np.linalg.norm(bv))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(av, bv) / (na * nb))


async def store_fingerprint(
    db: AsyncSession,
    sample_id: str,
    profile_id: str,
    embedding: list[float],
    method: str = _METHOD_MFCC,
) -> VoiceFingerprint:
    """Persist a fingerprint row for (sample_id, profile_id)."""
    row = VoiceFingerprint(
        sample_id=sample_id,
        profile_id=profile_id,
        embedding_json=json.dumps(embedding),
        method=method,
    )
    db.add(row)
    await db.flush()
    logger.info(
        "fingerprint_stored",
        fingerprint_id=row.id,
        sample_id=sample_id,
        profile_id=profile_id,
        method=method,
        dims=len(embedding),
    )
    return row


async def find_matching_profiles(
    db: AsyncSession,
    embedding: list[float],
    threshold: float | None = None,
    exclude_profile_id: str | None = None,
) -> list[VoiceProfile]:
    """Return profiles whose stored fingerprints exceed ``threshold`` similarity.

    Compares ``embedding`` against every stored fingerprint and returns the
    distinct set of profiles that match.  If ``exclude_profile_id`` is
    provided, fingerprints owned by that profile are ignored — useful when
    you want to find *other* profiles that sound similar to the sample you
    just uploaded.
    """
    effective_threshold = (
        threshold if threshold is not None else settings.fingerprint_match_threshold
    )

    query = select(VoiceFingerprint)
    if exclude_profile_id:
        query = query.where(VoiceFingerprint.profile_id != exclude_profile_id)
    result = await db.execute(query)
    rows = list(result.scalars().all())

    matched_profile_ids: set[str] = set()
    for row in rows:
        try:
            other = json.loads(row.embedding_json)
        except (ValueError, TypeError):
            continue
        score = cosine_similarity(embedding, other)
        if score >= effective_threshold:
            matched_profile_ids.add(row.profile_id)

    if not matched_profile_ids:
        return []

    profile_result = await db.execute(
        select(VoiceProfile).where(VoiceProfile.id.in_(matched_profile_ids))
    )
    return list(profile_result.scalars().all())
