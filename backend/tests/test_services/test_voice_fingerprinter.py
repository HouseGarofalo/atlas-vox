"""Tests for the voice fingerprinting service (SC-46)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_sample import AudioSample
from app.models.voice_fingerprint import VoiceFingerprint
from app.schemas.profile import ProfileCreate
from app.services.profile_service import create_profile
from app.services.voice_fingerprinter import (
    compute_fingerprint,
    cosine_similarity,
    find_matching_profiles,
    store_fingerprint,
)


SAMPLE_RATE = 22050


@pytest.fixture(autouse=True)
def _force_mfcc_path(monkeypatch):
    """Force the MFCC fallback — resemblyzer is optional and slow.

    Tests exercise the fast deterministic path so they stay under the
    end-to-end ``pytest`` budget.
    """
    monkeypatch.setattr(
        "app.services.voice_fingerprinter._try_resemblyzer",
        lambda _path: None,
    )


def _write_signal(path: Path, signal: np.ndarray, sr: int = SAMPLE_RATE) -> None:
    sf.write(str(path), signal.astype(np.float32), sr)


def _voice_like(seed: int = 0, length: int = SAMPLE_RATE * 2) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(length) / SAMPLE_RATE
    base = (
        0.3 * np.sin(2 * np.pi * (180 + seed * 5) * t)
        + 0.2 * np.sin(2 * np.pi * (360 + seed * 8) * t)
        + 0.1 * np.sin(2 * np.pi * (540 + seed * 11) * t)
    )
    noise = 0.01 * rng.standard_normal(length)
    return (base + noise).astype(np.float32)


async def _make_profile(db: AsyncSession, name: str, provider: str = "elevenlabs"):
    return await create_profile(db, ProfileCreate(name=name, provider_name=provider))


async def _add_sample(db: AsyncSession, profile_id: str, path: Path) -> AudioSample:
    sample = AudioSample(
        profile_id=profile_id,
        filename=path.name,
        original_filename=path.name,
        file_path=str(path),
        format="wav",
        file_size_bytes=path.stat().st_size,
        duration_seconds=2.0,
    )
    db.add(sample)
    await db.flush()
    return sample


# ---------------------------------------------------------------------------
# compute_fingerprint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_fingerprint_returns_vector(tmp_path: Path):
    wav = tmp_path / "voice.wav"
    _write_signal(wav, _voice_like(seed=1))
    embedding = await compute_fingerprint(wav)
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.asyncio
async def test_cosine_similarity_basic():
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(1.0)

    c = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, c) == pytest.approx(0.0, abs=1e-6)

    d = [-1.0, 0.0, 0.0]
    assert cosine_similarity(a, d) == pytest.approx(-1.0)


@pytest.mark.asyncio
async def test_cosine_similarity_handles_zero_and_mismatched():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
    assert cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0


# ---------------------------------------------------------------------------
# storage round-trip
# ---------------------------------------------------------------------------


async def test_store_fingerprint_roundtrip(
    db_session: AsyncSession, tmp_path: Path,
):
    profile = await _make_profile(db_session, "FP One")
    wav = tmp_path / "voice.wav"
    _write_signal(wav, _voice_like(seed=2))
    sample = await _add_sample(db_session, profile.id, wav)

    embedding = await compute_fingerprint(wav)
    row = await store_fingerprint(
        db_session,
        sample_id=sample.id,
        profile_id=profile.id,
        embedding=embedding,
    )
    assert row.id is not None

    # Round-trip: decode embedding JSON and ensure it matches.
    decoded = json.loads(row.embedding_json)
    assert decoded == embedding
    assert row.profile_id == profile.id
    assert row.sample_id == sample.id


# ---------------------------------------------------------------------------
# matching
# ---------------------------------------------------------------------------


async def test_find_matching_profiles_similar_embeddings_match(
    db_session: AsyncSession, tmp_path: Path,
):
    profile_a = await _make_profile(db_session, "Match A")
    profile_b = await _make_profile(db_session, "Match B")

    wav_a = tmp_path / "a.wav"
    wav_b = tmp_path / "b.wav"
    _write_signal(wav_a, _voice_like(seed=3))
    _write_signal(wav_b, _voice_like(seed=3))  # identical signal ⇒ identical embedding

    sample_a = await _add_sample(db_session, profile_a.id, wav_a)
    sample_b = await _add_sample(db_session, profile_b.id, wav_b)

    emb_a = await compute_fingerprint(wav_a)
    emb_b = await compute_fingerprint(wav_b)

    await store_fingerprint(
        db_session, sample_id=sample_a.id, profile_id=profile_a.id, embedding=emb_a
    )
    await store_fingerprint(
        db_session, sample_id=sample_b.id, profile_id=profile_b.id, embedding=emb_b
    )

    matches = await find_matching_profiles(
        db_session, emb_a, threshold=0.99, exclude_profile_id=profile_a.id
    )
    assert any(p.id == profile_b.id for p in matches)


async def test_find_matching_profiles_different_no_match(
    db_session: AsyncSession, tmp_path: Path,
):
    profile_a = await _make_profile(db_session, "Diff A")
    profile_b = await _make_profile(db_session, "Diff B")

    wav_a = tmp_path / "a.wav"
    wav_b = tmp_path / "b.wav"
    _write_signal(wav_a, _voice_like(seed=4))
    # Use a drastically different signal: a square-wave-ish pattern.
    length = SAMPLE_RATE * 2
    t = np.arange(length) / SAMPLE_RATE
    different = (np.sign(np.sin(2 * np.pi * 40 * t)) * 0.4).astype(np.float32)
    _write_signal(wav_b, different)

    sample_a = await _add_sample(db_session, profile_a.id, wav_a)
    sample_b = await _add_sample(db_session, profile_b.id, wav_b)

    emb_a = await compute_fingerprint(wav_a)
    emb_b = await compute_fingerprint(wav_b)

    await store_fingerprint(
        db_session, sample_id=sample_a.id, profile_id=profile_a.id, embedding=emb_a
    )
    await store_fingerprint(
        db_session, sample_id=sample_b.id, profile_id=profile_b.id, embedding=emb_b
    )

    # Pick a threshold higher than the naive MFCC mean can achieve on
    # unrelated signals.
    matches = await find_matching_profiles(
        db_session, emb_a, threshold=0.99, exclude_profile_id=profile_a.id
    )
    assert all(p.id != profile_b.id for p in matches)


async def test_threshold_respected(db_session: AsyncSession, tmp_path: Path):
    profile_a = await _make_profile(db_session, "Thresh A")
    profile_b = await _make_profile(db_session, "Thresh B")

    wav_a = tmp_path / "a.wav"
    wav_b = tmp_path / "b.wav"
    _write_signal(wav_a, _voice_like(seed=5))
    _write_signal(wav_b, _voice_like(seed=5))

    sample_a = await _add_sample(db_session, profile_a.id, wav_a)
    sample_b = await _add_sample(db_session, profile_b.id, wav_b)

    emb = await compute_fingerprint(wav_a)

    await store_fingerprint(
        db_session, sample_id=sample_a.id, profile_id=profile_a.id, embedding=emb
    )
    await store_fingerprint(
        db_session, sample_id=sample_b.id, profile_id=profile_b.id, embedding=emb
    )

    # With a threshold above 1.0 no match can exceed it.
    matches = await find_matching_profiles(
        db_session, emb, threshold=1.0001, exclude_profile_id=profile_a.id
    )
    assert matches == []

    # With a threshold of 0, everything matches.
    matches = await find_matching_profiles(
        db_session, emb, threshold=0.0, exclude_profile_id=profile_a.id
    )
    assert any(p.id == profile_b.id for p in matches)
