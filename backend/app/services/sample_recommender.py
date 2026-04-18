"""SL-29 — active-learning sample recommender.

Given a profile's phoneme-coverage report (DT-31), recommend the next N
sentences the user should record to maximally fill the remaining gaps.
Uses a greedy set-cover over a curated sentence bank. The bank ships with
~60 phonetically-diverse sentences (CMU Arctic subset + extras); each is
pre-tokenised into its phoneme set at load time so recommendation is O(N·B)
where N is bank size and B is the requested recommendation count (typically
10-20).

Design notes:
- Set-cover is NP-hard; greedy gives a (1 + ln(|U|)) approximation which is
  well within what a user needs ("record these 10 things").
- We never recommend a sentence the user already recorded (transcript match).
- Ties break by sentence length ascending — shorter sentences are easier
  to read cleanly.
- If ``phonemizer`` isn't available on the host we fall back to the same
  character-bigram approximation ``phoneme_coverage`` uses so the recommender
  still returns useful sentences; the report includes ``method`` so callers
  know which tokenisation was used.
"""

from __future__ import annotations

import threading
from collections import Counter
from dataclasses import asdict, dataclass, field
from functools import lru_cache

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_sample import AudioSample
from app.services.phoneme_coverage import (
    REFERENCE_PHONEMES,
    _bigram_approximation,
    _phonemize_safe,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Curated sentence bank
# ---------------------------------------------------------------------------

# A mix of CMU Arctic (public-domain phonetically-balanced corpus) sentences
# and supplementary phrases specifically chosen to surface phonemes that
# Arctic under-represents (e.g. /ʒ/, /ɔɪ/, /aʊ/).
_EN_SENTENCE_BANK: tuple[str, ...] = (
    # CMU Arctic-style (Harvard) sentences — broad coverage.
    "The birch canoe slid on the smooth planks.",
    "Glue the sheet to the dark blue background.",
    "It's easy to tell the depth of a well.",
    "These days a chicken leg is a rare dish.",
    "Rice is often served in round bowls.",
    "The juice of lemons makes fine punch.",
    "The box was thrown beside the parked truck.",
    "The hogs were fed chopped corn and garbage.",
    "Four hours of steady work faced us.",
    "A large size in stockings is hard to sell.",
    "The boy was there when the sun rose.",
    "A rod is used to catch pink salmon.",
    "The source of the huge river is the clear spring.",
    "Kick the ball straight and follow through.",
    "Help the woman get back to her feet.",
    "A pot of tea helps to pass the evening.",
    "Smoky fires lack flame and heat.",
    "The soft cushion broke the man's fall.",
    "The salt breeze came across from the sea.",
    "The girl at the booth sold fifty bonds.",
    # Phoneme-targeted supplements.
    "She measured the azure treasure by leisure.",  # /ʒ/
    "The boy's choice was to enjoy the toys.",  # /ɔɪ/
    "Loud crowds gathered around the round house.",  # /aʊ/
    "This thin cloth is worth both your mother's effort.",  # /θ/ and /ð/
    "Jack judged the badge on the edge of the bridge.",  # /dʒ/ and /tʃ/
    "The eager singer sang songs of hunger and longing.",  # /ŋ/
    "Red lorry, yellow lorry, really rural roads.",  # /ɹ/ / /l/
    "Sunshine melted yesterday's icy afternoon slowly.",  # /ʃ/ and clusters
    "Fresh flowers from the farm filled five vases.",  # /f/ /v/
    "Whether weather will allow walking where we wish is why we wonder.",  # /w/ and vowels
    "How could ooze move through a new blue tube?",  # /u/ and /ʊ/
    "Bright white kites fly high in windy nights.",  # /aɪ/
    "Late eight-year-olds ate ripe baked pears.",  # /eɪ/, /ɛ/
    "Oh, the old goat showed the cold road home.",  # /oʊ/
    "Father's calm palm patted the starving dog's head.",  # /ɑ/ /ʌ/
    "Should sugar or pudding be put in the push cart?",  # /ʊ/ /ʃ/
    # Short calibration sentences.
    "Hello.",
    "Thank you very much.",
    "I'll be right back.",
    "Good morning, how are you today?",
    "Please leave a message after the tone.",
    "Yes, that sounds perfect.",
    "The quick brown fox jumps over the lazy dog.",  # pangram
    "Pack my box with five dozen liquor jugs.",  # pangram
    # Numbers / dates / times for say-as coverage.
    "Call me at four fifteen on March third.",
    "The total comes to one hundred and twenty-three dollars.",
    "Your flight departs at seven forty-five p.m.",
    # Emotional range prompts.
    "I can't believe we actually won!",
    "I'm sorry, I didn't mean to upset you.",
    "Please, just let me explain one more time.",
    "That was, without a doubt, the best meal I've ever had.",
    # Long-form narration samples.
    "Under a pale crescent moon the narrator began her tale, weaving words like soft silver thread between the listening trees.",
    "There was once a clockmaker in a tiny mountain village whose pendulums chimed in perfect, patient harmony.",
    "In the quiet hours before dawn, when even the streetlights seemed to hum softly to themselves, she opened the old door.",
)


@dataclass(frozen=True)
class _BankEntry:
    """A single candidate sentence with its pre-computed phoneme set."""

    text: str
    phonemes: frozenset[str]
    length: int


@dataclass
class RecommendedSentence:
    """Public-facing recommendation row."""

    text: str
    fills_gaps: list[str]
    gap_fill_count: int
    priority: int  # 1-based ordering — 1 = most valuable recommendation

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SampleRecommendation:
    """Bundle returned by :func:`recommend_next_samples`."""

    profile_id: str
    method: str  # "phonemizer" or "bigram_approx"
    gap_count_before: int
    gap_count_after: int
    recommendations: list[RecommendedSentence] = field(default_factory=list)
    already_recorded_skipped: int = 0

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "method": self.method,
            "gap_count_before": self.gap_count_before,
            "gap_count_after": self.gap_count_after,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "already_recorded_skipped": self.already_recorded_skipped,
        }


# Bank pre-computation is guarded by a lock so concurrent first-touch
# doesn't run phonemizer twice. Keyed by language + method so the fallback
# bank is distinct from the real one.
_bank_cache: dict[tuple[str, str], tuple[_BankEntry, ...]] = {}
_bank_lock = threading.Lock()


def _sentence_to_phonemes(sentence: str, language: str, method_hint: str) -> tuple[frozenset[str], str]:
    """Tokenise one sentence into a phoneme set. Returns (phonemes, method)."""
    if method_hint != "bigram_approx":
        phones = _phonemize_safe(sentence, language=language)
        if phones is not None:
            reference = REFERENCE_PHONEMES.get(language, REFERENCE_PHONEMES["en"])
            return frozenset(p for p in phones if p in reference), "phonemizer"
    phones = _bigram_approximation(sentence)
    reference = REFERENCE_PHONEMES.get(language, REFERENCE_PHONEMES["en"])
    return frozenset(p for p in phones if p in reference), "bigram_approx"


def _build_bank(language: str, prefer_method: str) -> tuple[_BankEntry, ...]:
    """Tokenise the sentence bank once per (language, method). Cached."""
    key = (language, prefer_method)
    cached = _bank_cache.get(key)
    if cached is not None:
        return cached
    with _bank_lock:
        cached = _bank_cache.get(key)
        if cached is not None:
            return cached
        source = _EN_SENTENCE_BANK  # Only English bank ships today.
        entries: list[_BankEntry] = []
        method_used = prefer_method
        for sent in source:
            phones, method_used = _sentence_to_phonemes(sent, language, prefer_method)
            entries.append(_BankEntry(text=sent, phonemes=phones, length=len(sent)))
        logger.info(
            "sample_recommender_bank_built",
            language=language,
            method=method_used,
            size=len(entries),
        )
        result = tuple(entries)
        _bank_cache[key] = result
        return result


def _greedy_set_cover(
    bank: tuple[_BankEntry, ...],
    gaps: set[str],
    n: int,
    exclude_texts: set[str],
) -> list[RecommendedSentence]:
    """Classic greedy set-cover with tie-breaking on length ascending.

    If ``n`` exceeds the number of sentences that improve coverage, we
    top up with "variety" picks (phoneme-diverse, novel-content) so the
    caller always gets up to ``n`` recommendations to surface — users
    asking for 10 shouldn't see 1 just because their bigram fallback
    saturated. Variety picks have ``gap_fill_count == 0``.
    """
    remaining = set(gaps)
    chosen: list[RecommendedSentence] = []
    used_indices: set[int] = set()
    priority = 1
    while remaining and len(chosen) < n:
        best_idx: int | None = None
        best_gain: frozenset[str] = frozenset()
        best_length: int = 10**9
        for idx, entry in enumerate(bank):
            if idx in used_indices:
                continue
            if entry.text in exclude_texts:
                continue
            gain = entry.phonemes & remaining
            if not gain:
                continue
            # Strictly larger gain wins; tie breaks on shorter sentence.
            if (
                len(gain) > len(best_gain)
                or (len(gain) == len(best_gain) and entry.length < best_length)
            ):
                best_idx = idx
                best_gain = frozenset(gain)
                best_length = entry.length
        if best_idx is None:
            break  # No remaining bank entry fills any remaining gap.
        used_indices.add(best_idx)
        entry = bank[best_idx]
        chosen.append(
            RecommendedSentence(
                text=entry.text,
                fills_gaps=sorted(best_gain),
                gap_fill_count=len(best_gain),
                priority=priority,
            )
        )
        priority += 1
        remaining -= set(best_gain)

    # Top up with variety picks — the user asked for N sentences and we
    # want to keep them productively recording even when coverage is
    # theoretically maxed.  Pick sentences with the largest phoneme set
    # (broadest practice material) that we haven't already used.
    if len(chosen) < n:
        candidates = [
            (idx, entry)
            for idx, entry in enumerate(bank)
            if idx not in used_indices and entry.text not in exclude_texts
        ]
        # Sort by descending phoneme set size; break ties on shorter sentence.
        candidates.sort(key=lambda pair: (-len(pair[1].phonemes), pair[1].length))
        for idx, entry in candidates:
            if len(chosen) >= n:
                break
            chosen.append(
                RecommendedSentence(
                    text=entry.text,
                    fills_gaps=[],
                    gap_fill_count=0,
                    priority=priority,
                )
            )
            priority += 1
    return chosen


@lru_cache(maxsize=1)
def _normalize(s: str) -> str:
    return s.strip().lower()


async def recommend_next_samples(
    db: AsyncSession,
    profile_id: str,
    *,
    count: int = 10,
    language: str = "en",
) -> SampleRecommendation:
    """Recommend up to ``count`` sentences that fill this profile's gaps.

    Workflow:
      1. Pull all sample transcripts for ``profile_id``.
      2. Compute phoneme gaps vs the curated reference for ``language``.
      3. Tokenise each bank sentence and run greedy set-cover, excluding
         sentences whose text already matches a recorded transcript.
      4. Return the top ``count`` sentences with explanatory metadata.
    """
    # 1. Load existing transcripts.
    result = await db.execute(
        select(AudioSample.transcript).where(AudioSample.profile_id == profile_id)
    )
    rows = [r[0] for r in result.all() if r[0]]

    # 2. Determine current phoneme coverage (reuse DT-31 tokenisation pattern).
    reference = REFERENCE_PHONEMES.get(language, REFERENCE_PHONEMES["en"])
    joined = " ".join(rows)
    method = "phonemizer"
    if joined.strip():
        phones = _phonemize_safe(joined, language=language)
        if phones is None:
            phones = _bigram_approximation(joined)
            method = "bigram_approx"
        present = {p for p in Counter(phones) if p in reference}
    else:
        present = set()
        # We can't know which tokeniser would have been used — try once.
        if _phonemize_safe("hello", language=language) is None:
            method = "bigram_approx"

    gaps = reference - present
    gap_count_before = len(gaps)

    # 3. Set-cover.
    bank = _build_bank(language, prefer_method=method)
    exclude = {t.strip() for t in rows}
    # Case-insensitive match for "already recorded" detection.
    exclude_ci = {_normalize(t) for t in exclude}
    filtered_bank = tuple(e for e in bank if _normalize(e.text) not in exclude_ci)

    recommendations = _greedy_set_cover(
        filtered_bank, gaps, n=count, exclude_texts=set()
    )

    covered_after: set[str] = present.copy()
    for rec in recommendations:
        covered_after.update(rec.fills_gaps)
    gap_count_after = max(0, len(reference) - len(covered_after))

    logger.info(
        "sample_recommender_done",
        profile_id=profile_id,
        method=method,
        gap_count_before=gap_count_before,
        gap_count_after=gap_count_after,
        recommendations=len(recommendations),
    )

    return SampleRecommendation(
        profile_id=profile_id,
        method=method,
        gap_count_before=gap_count_before,
        gap_count_after=gap_count_after,
        recommendations=recommendations,
        already_recorded_skipped=len(bank) - len(filtered_bank),
    )


def clear_bank_cache() -> None:
    """Expose the cache reset for tests that change the sentence list."""
    with _bank_lock:
        _bank_cache.clear()
