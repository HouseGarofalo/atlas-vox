"""P2-24: pronunciation cache must evict when it exceeds the max-size cap.

Without this guard, atlas-vox's pronunciation cache would grow without
bound across profiles, leaking memory in long-running worker processes.
"""

from __future__ import annotations

import time

import pytest

from app.services import pronunciation_service
from app.services.pronunciation_service import (
    _PRONUNCIATION_CACHE_MAX_SIZE,
    _pronunciation_cache,
    apply_pronunciation,
    clear_cache,
)


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_cache()
    yield
    clear_cache()


class _FakeResult:
    def __init__(self, entries):
        self._entries = entries

    def scalars(self):
        class _S:
            def __init__(self, e):
                self._e = e

            def all(self):
                return self._e

        return _S(self._entries)


class _FakeSession:
    """Minimal async DB session that returns a fixed empty-entries result."""

    async def execute(self, _stmt):
        return _FakeResult([])


@pytest.mark.asyncio
async def test_cache_evicts_to_half_when_exceeding_max_size():
    """Crossing MAX_SIZE must trigger half-eviction (oldest first)."""
    db = _FakeSession()

    # Seed cache past the ceiling. For each unique profile_id the service
    # inserts both "__global__" and the profile key, but "__global__" is
    # shared across calls so the cache only grows by one entry per call
    # after the first. To saturate it quickly we simulate direct insertion
    # with staggered timestamps so the oldest entries are deterministic.
    now = time.monotonic()
    for i in range(_PRONUNCIATION_CACHE_MAX_SIZE + 10):
        _pronunciation_cache[f"pre-seed-{i}"] = ([], now - (1000 - i))
    assert len(_pronunciation_cache) > _PRONUNCIATION_CACHE_MAX_SIZE

    # A fresh apply_pronunciation call for a new profile triggers the
    # eviction branch.
    await apply_pronunciation(db, "hello world", "brand-new-profile")

    # Post-eviction: cache must be at or below the ceiling.
    assert len(_pronunciation_cache) <= _PRONUNCIATION_CACHE_MAX_SIZE

    # The oldest pre-seed entries (lowest index = smallest timestamp in our
    # staggering) must have been dropped.
    assert "pre-seed-0" not in _pronunciation_cache


@pytest.mark.asyncio
async def test_cache_does_not_evict_below_max_size():
    """Stay under MAX_SIZE → no eviction."""
    db = _FakeSession()
    await apply_pronunciation(db, "hello", "profile-a")
    snapshot = set(_pronunciation_cache.keys())
    await apply_pronunciation(db, "hello", "profile-b")
    # Both profiles (plus __global__) now cached; nothing evicted.
    for key in snapshot:
        assert key in _pronunciation_cache


@pytest.mark.asyncio
async def test_clear_cache_wipes_everything():
    db = _FakeSession()
    await apply_pronunciation(db, "hello", "profile-a")
    assert len(_pronunciation_cache) > 0
    clear_cache()
    assert len(_pronunciation_cache) == 0


@pytest.mark.asyncio
async def test_invalidate_cache_drops_single_bucket():
    db = _FakeSession()
    await apply_pronunciation(db, "hello", "profile-zzz")
    assert "profile-zzz" in _pronunciation_cache
    pronunciation_service.invalidate_cache("profile-zzz")
    assert "profile-zzz" not in _pronunciation_cache
