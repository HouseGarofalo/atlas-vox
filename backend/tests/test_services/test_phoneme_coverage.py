"""Tests for the phoneme coverage analyzer (DT-31)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_sample import AudioSample
from app.schemas.profile import ProfileCreate
from app.services.phoneme_coverage import (
    REFERENCE_PHONEMES,
    _bigram_approximation,
    _tokenize_ipa,
    analyze_profile_coverage,
)
from app.services.profile_service import create_profile


@pytest.mark.asyncio
async def test_empty_profile_returns_zero_coverage(db_session: AsyncSession):
    profile = await create_profile(
        db_session,
        ProfileCreate(name="Empty Coverage Profile", provider_name="kokoro"),
    )
    report = await analyze_profile_coverage(db_session, profile.id, language="en")
    assert report.coverage_pct == 0.0
    assert report.sample_count == 0
    assert report.present_phonemes == []
    # Every reference phoneme should be listed as a gap.
    assert set(report.gaps) == REFERENCE_PHONEMES["en"]


@pytest.mark.asyncio
async def test_profile_with_pangram_has_nonzero_coverage(
    db_session: AsyncSession, tmp_path,
):
    """A pangram transcript should cover a healthy slice of phonemes."""
    profile = await create_profile(
        db_session,
        ProfileCreate(name="Pangram Coverage", provider_name="kokoro"),
    )
    # Add two transcripts that together cover a lot of English phonemes.
    transcripts = [
        "The quick brown fox jumps over the lazy dog.",
        "She sells seashells by the seashore in the thick fog.",
    ]
    for i, tx in enumerate(transcripts):
        wav = tmp_path / f"s_{i}.wav"
        wav.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
        db_session.add(AudioSample(
            profile_id=profile.id,
            filename=wav.name,
            original_filename=wav.name,
            file_path=str(wav),
            format="wav",
            duration_seconds=5.0,
            transcript=tx,
        ))
    await db_session.flush()

    report = await analyze_profile_coverage(db_session, profile.id, language="en")
    assert report.sample_count == 2
    # Regardless of method we expect at least *some* coverage for pangrams.
    assert report.coverage_pct > 0.0
    # The bigram fallback also produces non-empty present_phonemes (e.g. 't',
    # 's', 'k' overlap with reference IPA for those exact characters).
    assert isinstance(report.present_phonemes, list)
    assert report.method in ("phonemizer", "bigram_approx")


@pytest.mark.asyncio
async def test_samples_without_transcripts_are_ignored(
    db_session: AsyncSession, tmp_path,
):
    profile = await create_profile(
        db_session,
        ProfileCreate(name="No Transcripts Profile", provider_name="kokoro"),
    )
    wav = tmp_path / "no_tx.wav"
    wav.write_bytes(b"RIFF\x00\x00\x00\x00")
    db_session.add(AudioSample(
        profile_id=profile.id,
        filename=wav.name,
        original_filename=wav.name,
        file_path=str(wav),
        format="wav",
        duration_seconds=5.0,
        transcript=None,
    ))
    await db_session.flush()

    report = await analyze_profile_coverage(db_session, profile.id, language="en")
    assert report.sample_count == 1
    assert report.transcript_char_count == 0
    assert report.coverage_pct == 0.0


class TestTokenization:
    def test_digraphs_are_single_tokens(self):
        assert _tokenize_ipa("tʃæt") == ["tʃ", "æ", "t"]

    def test_stress_marks_are_stripped(self):
        tokens = _tokenize_ipa("ˈhɛloʊ")
        assert "\u02c8" not in tokens
        assert "h" in tokens

    def test_length_mark_stripped(self):
        assert "\u02d0" not in _tokenize_ipa("biː")


class TestBigramApproximation:
    def test_returns_letters_plus_bigrams(self):
        tokens = _bigram_approximation("hi there")
        # Single letters present
        assert "h" in tokens
        assert "t" in tokens
        # Bigrams from the word "there"
        assert "th" in tokens
        assert "er" in tokens

    def test_non_alpha_stripped(self):
        tokens = _bigram_approximation("hi! 123 there.")
        assert "1" not in tokens
        assert "!" not in tokens
