"""Phoneme-coverage analyzer — DT-31.

Given the transcripts of all audio samples in a profile, estimate which
phonemes have been recorded and which are still missing.  When the
``phonemizer`` package + eSpeak backend are available we use real IPA
transcription; otherwise we fall back to a character-bigram approximation so
the endpoint is still useful on installs without the native dependency.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_sample import AudioSample

logger = structlog.get_logger(__name__)


# Curated reference phoneme inventories. Values are the standard IPA symbols
# expected to appear in conversational speech for that language. English
# (General American, 44 phonemes — CMU-style inventory converted to IPA).
REFERENCE_PHONEMES: dict[str, set[str]] = {
    "en": {
        # Vowels / diphthongs
        "i", "ɪ", "e", "ɛ", "æ", "ɑ", "ɔ", "o", "ʊ", "u",
        "ʌ", "ə", "ɝ", "ɚ", "aɪ", "aʊ", "ɔɪ", "eɪ", "oʊ",
        # Stops
        "p", "b", "t", "d", "k", "ɡ",
        # Affricates
        "tʃ", "dʒ",
        # Fricatives
        "f", "v", "θ", "ð", "s", "z", "ʃ", "ʒ", "h",
        # Nasals
        "m", "n", "ŋ",
        # Liquids / glides
        "l", "ɹ", "j", "w",
    },
}


@dataclass
class PhonemeCoverageReport:
    """Result payload returned by :func:`analyze_profile_coverage`."""

    profile_id: str
    language: str
    method: str  # "phonemizer" or "bigram_approx"
    sample_count: int
    transcript_char_count: int
    coverage_pct: float
    expected_phoneme_count: int
    present_phonemes: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    over_representation: list[tuple[str, int]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["over_representation"] = [
            {"phoneme": p, "count": c} for p, c in self.over_representation
        ]
        return d


def _phonemize_safe(text: str, language: str = "en") -> list[str] | None:
    """Attempt to phonemize ``text`` using eSpeak. Returns ``None`` on failure.

    We keep the dependency optional — many dev installs don't have espeak
    available, so callers must fall back when this returns ``None``.
    """
    try:
        from phonemizer import phonemize  # type: ignore[import-not-found]
    except ImportError:
        return None

    try:
        phones = phonemize(
            text,
            language=language,
            backend="espeak",
            strip=True,
            preserve_punctuation=False,
            with_stress=False,
        )
    except Exception as exc:  # espeak misconfig, runtime errors, etc.
        logger.warning("phonemizer_failed", error=str(exc), language=language)
        return None

    tokens: list[str] = []
    for chunk in phones.split():
        tokens.extend(_tokenize_ipa(chunk))
    return tokens


# IPA digraphs we treat as a single token (two-char affricates / diphthongs
# commonly emitted by eSpeak).
_IPA_DIGRAPHS = {"tʃ", "dʒ", "aɪ", "aʊ", "ɔɪ", "eɪ", "oʊ"}


def _tokenize_ipa(s: str) -> list[str]:
    """Split an IPA string into phoneme tokens (greedy digraph first)."""
    tokens: list[str] = []
    i = 0
    while i < len(s):
        if i + 1 < len(s) and s[i : i + 2] in _IPA_DIGRAPHS:
            tokens.append(s[i : i + 2])
            i += 2
            continue
        ch = s[i]
        # Skip stress / length marks and whitespace.
        if ch in "\u02c8\u02cc\u02d0 \t\n":
            i += 1
            continue
        tokens.append(ch)
        i += 1
    return tokens


def _bigram_approximation(text: str) -> list[str]:
    """Fallback: treat each lowercase letter + each bigram as a 'phoneme-ish' token.

    Gives a very rough signal — enough to detect wildly under-covered
    corpora ("profile has only sampled words with 'a' and 'e'") without
    pretending to be real phonemization.
    """
    cleaned = "".join(ch.lower() for ch in text if ch.isalpha() or ch.isspace())
    tokens: list[str] = list(cleaned.replace(" ", ""))
    # Add word-internal bigrams so digraphs like "ch", "sh", "th", "ng" show up.
    for word in cleaned.split():
        for i in range(len(word) - 1):
            tokens.append(word[i : i + 2])
    return tokens


async def analyze_profile_coverage(
    db: AsyncSession,
    profile_id: str,
    language: str = "en",
) -> PhonemeCoverageReport:
    """Build a phoneme-coverage report for ``profile_id``.

    Reads every sample's transcript, phonemizes the concatenation, then
    compares against the curated reference inventory for ``language``.
    Samples without a transcript contribute nothing.
    """
    result = await db.execute(
        select(AudioSample).where(AudioSample.profile_id == profile_id)
    )
    samples = list(result.scalars().all())

    transcripts = [s.transcript for s in samples if s.transcript]
    text = " ".join(transcripts).strip()
    reference = REFERENCE_PHONEMES.get(
        language, REFERENCE_PHONEMES["en"],
    )

    warnings: list[str] = []
    if not text:
        return PhonemeCoverageReport(
            profile_id=profile_id,
            language=language,
            method="none",
            sample_count=len(samples),
            transcript_char_count=0,
            coverage_pct=0.0,
            expected_phoneme_count=len(reference),
            present_phonemes=[],
            gaps=sorted(reference),
            over_representation=[],
            warnings=["No transcripts available for this profile"],
        )

    phones = _phonemize_safe(text, language=language)
    if phones is None:
        warnings.append(
            "phonemizer unavailable — falling back to character-bigram approximation"
        )
        phones = _bigram_approximation(text)
        method = "bigram_approx"
    else:
        method = "phonemizer"

    counter = Counter(phones)
    present = {p for p in counter if p in reference}
    # Compute coverage against the reference inventory (real phonemes only).
    coverage_pct = (len(present) / len(reference) * 100.0) if reference else 0.0
    gaps = sorted(reference - present)
    # Most-frequent phonemes that *are* in the reference set.
    top = [
        (p, c) for p, c in counter.most_common() if p in reference
    ][:5]

    return PhonemeCoverageReport(
        profile_id=profile_id,
        language=language,
        method=method,
        sample_count=len(samples),
        transcript_char_count=len(text),
        coverage_pct=round(coverage_pct, 2),
        expected_phoneme_count=len(reference),
        present_phonemes=sorted(present),
        gaps=gaps,
        over_representation=top,
        warnings=warnings,
    )
