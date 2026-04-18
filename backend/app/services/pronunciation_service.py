"""Pronunciation lexicon service — SSML phoneme injection with TTL cache.

Extracted from ``synthesis_service`` (P2-17). Owns the in-memory lookup cache,
compiled regex cache, and the async lookup/replace logic used by synthesis.
"""

from __future__ import annotations

import asyncio
import re
import time

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pronunciation_entry import PronunciationEntry

logger = structlog.get_logger(__name__)


# In-memory pronunciation cache: keyed by profile_id, stores (entries, timestamp).
# Global entries (profile_id=None) are cached under the key "__global__".
_pronunciation_cache: dict[str, tuple[list, float]] = {}
_PRONUNCIATION_CACHE_TTL = 60.0  # seconds
_PRONUNCIATION_CACHE_MAX_SIZE = 100

# Compiled regex cache for pronunciation patterns.
_regex_cache: dict[str, re.Pattern] = {}

# Lock for thread-safe pronunciation cache access.
_cache_lock = asyncio.Lock()


def invalidate_cache(profile_id: str | None = None) -> None:
    """Invalidate cached entries.

    If ``profile_id`` is None, only the global cache bucket is dropped.
    Pass a specific profile ID to drop that profile's bucket.
    """
    key = profile_id or "__global__"
    _pronunciation_cache.pop(key, None)


def clear_cache() -> None:
    """Drop every cached bucket (used after bulk imports)."""
    _pronunciation_cache.clear()


async def apply_pronunciation(db: AsyncSession, text: str, profile_id: str) -> str:
    """Replace words matching pronunciation dictionary entries with SSML phoneme tags.

    Looks up global entries (``profile_id IS NULL``) and profile-specific
    entries. Uses an in-memory cache with TTL to avoid repeated DB queries
    during batch synthesis. Returns the original text unchanged when no
    entries apply.
    """
    now = time.monotonic()
    entries: list = []

    cache_key_global = "__global__"
    cache_key_profile = profile_id

    async with _cache_lock:
        cached_global = _pronunciation_cache.get(cache_key_global)
        cached_profile = _pronunciation_cache.get(cache_key_profile)

        if (
            cached_global is not None
            and (now - cached_global[1]) < _PRONUNCIATION_CACHE_TTL
            and cached_profile is not None
            and (now - cached_profile[1]) < _PRONUNCIATION_CACHE_TTL
        ):
            entries = cached_global[0] + cached_profile[0]
        else:
            result = await db.execute(
                select(PronunciationEntry).where(
                    or_(
                        PronunciationEntry.profile_id.is_(None),
                        PronunciationEntry.profile_id == profile_id,
                    )
                )
            )
            all_entries = result.scalars().all()

            global_entries = [e for e in all_entries if e.profile_id is None]
            profile_entries = [e for e in all_entries if e.profile_id == profile_id]

            _pronunciation_cache[cache_key_global] = (global_entries, now)
            _pronunciation_cache[cache_key_profile] = (profile_entries, now)

            # Evict oldest entries if cache exceeds max size.
            if len(_pronunciation_cache) > _PRONUNCIATION_CACHE_MAX_SIZE:
                oldest_keys = sorted(
                    _pronunciation_cache,
                    key=lambda k: _pronunciation_cache[k][1],
                )[: _PRONUNCIATION_CACHE_MAX_SIZE // 2]
                for k in oldest_keys:
                    del _pronunciation_cache[k]

            entries = global_entries + profile_entries

    if not entries:
        return text

    # Apply replacements (case-insensitive word boundary matching).
    for entry in entries:
        cache_key = entry.word.lower()
        pattern = _regex_cache.get(cache_key)
        if pattern is None:
            pattern = re.compile(rf"\b{re.escape(entry.word)}\b", re.IGNORECASE)
            _regex_cache[cache_key] = pattern

        replacement = f'<phoneme alphabet="ipa" ph="{entry.ipa}">{entry.word}</phoneme>'
        text = pattern.sub(replacement, text)

    return text
