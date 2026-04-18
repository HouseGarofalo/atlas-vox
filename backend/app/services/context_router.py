"""SL-30 — context-adaptive voice routing.

Given a block of input text, classify it into a "context" (conversational,
narrative, emotional, technical, dialogue, long-form) and recommend the
voice profile from the caller's library that best matches.

Design:
  - v1 is a transparent heuristic stack — regex + length + punctuation
    + dialogue tags. No ML dependency; works on every install. The
    ``ContextClassifier`` returns a ranked list of ``ContextScore`` rows
    so callers can inspect the decision.
  - v1.5 reads the preference_aggregator output (SL-26) when available so
    routing biases toward the voices this user has historically thumbs-up'd
    for similar text. Graceful if SL-26 hasn't populated yet.
  - v2 could swap the classifier for an LLM call or a learned model; the
    ``classify_text`` → ``rank_profiles`` split is the seam.

The recommender output is advisory — the UI surfaces "Atlas suggests…"
with a one-click accept; it never routes automatically.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Iterable

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice_profile import VoiceProfile

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Context taxonomy + feature signals
# ---------------------------------------------------------------------------


# Six contexts the router recognises. Keep the list small — the UI surfaces
# one recommendation per text, not a fan-out of options.
Context = str
CONTEXTS: tuple[Context, ...] = (
    "conversational",
    "narrative",
    "emotional",
    "technical",
    "dialogue",
    "long_form",
)


@dataclass
class ContextScore:
    """One row of the classifier's ranked output."""

    context: Context
    score: float  # 0..1 — higher = more confident
    signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# Keyword buckets. Kept small and distinctive — broad matches dilute the
# signal. Each bucket contributes to exactly one context class.
_EMOTIONAL_MARKERS = re.compile(
    r"\b(love|hate|afraid|terrified|excited|sad|angry|furious|thrilled|"
    r"devastated|heartbroken|overjoyed|crushed|grief|joy|tears|weeping|"
    r"shouted|whispered|sobbed)\b",
    re.IGNORECASE,
)
_TECHNICAL_MARKERS = re.compile(
    r"\b(api|http|json|kubernetes|docker|sql|regex|algorithm|server|"
    r"database|endpoint|function|variable|exception|stack trace|commit|"
    r"pull request|CPU|GPU|latency|throughput|bandwidth|cache|token|"
    r"payload|schema|error code|status 4\d\d|status 5\d\d)\b",
    re.IGNORECASE,
)
_NARRATIVE_MARKERS = re.compile(
    r"\b(once upon a time|long ago|in the year|there lived|narrator|"
    r"chapter|the tale|the story|once, in|his eyes|her eyes|the morning|"
    r"that evening|the wind|the forest|the kingdom|as night fell)\b",
    re.IGNORECASE,
)
_CONVERSATIONAL_MARKERS = re.compile(
    r"\b(hey|hi|hello|yeah|yep|nope|lol|wanna|gonna|kinda|sorta|okay|ok|"
    r"right\?|you know|by the way|anyway|gotta|alright|thanks|thx)\b",
    re.IGNORECASE,
)

_DIALOGUE_QUOTES = re.compile(r'["\u201c\u201d]([^"\u201c\u201d]{2,})["\u201c\u201d]')
_DIALOGUE_TAGS = re.compile(r"\b(said|asked|replied|shouted|whispered|cried)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def classify_text(text: str) -> list[ContextScore]:
    """Return contexts ranked most-likely → least-likely.

    Stable, deterministic, no external calls. A non-empty input always
    returns a fully-ordered list with at least one context scoring > 0 so
    callers can always present *some* recommendation.
    """
    if not text or not text.strip():
        return [ContextScore(context="conversational", score=0.0, signals=["empty input"])]

    scores: dict[Context, float] = dict.fromkeys(CONTEXTS, 0.0)
    signals: dict[Context, list[str]] = {c: [] for c in CONTEXTS}
    char_count = len(text)
    word_count = len(text.split())
    sentence_count = max(1, len(re.findall(r"[.!?]+", text)))
    avg_sentence_len = word_count / sentence_count

    # Long form: sheer length dominates. Bonus for many sentences.
    if char_count > 600:
        scores["long_form"] += 0.5
        signals["long_form"].append(f"{char_count} characters")
    if sentence_count >= 8:
        scores["long_form"] += 0.3
        signals["long_form"].append(f"{sentence_count} sentences")

    # Dialogue: quoted strings + speech tags.
    quotes = _DIALOGUE_QUOTES.findall(text)
    tags = len(_DIALOGUE_TAGS.findall(text))
    if quotes:
        scores["dialogue"] += min(0.7, 0.25 + 0.1 * len(quotes))
        signals["dialogue"].append(f"{len(quotes)} quoted span(s)")
    if tags:
        scores["dialogue"] += min(0.3, 0.1 * tags)
        signals["dialogue"].append(f"{tags} dialogue tag(s)")

    # Emotional: markers + exclamation density.
    emotions = len(_EMOTIONAL_MARKERS.findall(text))
    exclamations = text.count("!")
    if emotions:
        scores["emotional"] += min(0.6, 0.2 + 0.1 * emotions)
        signals["emotional"].append(f"{emotions} emotion word(s)")
    if exclamations >= 2:
        scores["emotional"] += min(0.3, 0.1 * exclamations)
        signals["emotional"].append(f"{exclamations} exclamation(s)")

    # Technical: markers + code-ish punctuation + numbers.
    tech = len(_TECHNICAL_MARKERS.findall(text))
    code_punct = sum(text.count(ch) for ch in "{};[]()")
    has_url = bool(re.search(r"https?://\S+", text))
    if tech:
        scores["technical"] += min(0.6, 0.2 + 0.1 * tech)
        signals["technical"].append(f"{tech} technical term(s)")
    if code_punct > 6:
        scores["technical"] += 0.2
        signals["technical"].append(f"{code_punct} code punctuation char(s)")
    if has_url:
        scores["technical"] += 0.15
        signals["technical"].append("URL present")

    # Narrative: literary markers + long sentences without dialogue.
    narr = len(_NARRATIVE_MARKERS.findall(text))
    if narr:
        scores["narrative"] += min(0.6, 0.25 + 0.1 * narr)
        signals["narrative"].append(f"{narr} narrative phrase(s)")
    if avg_sentence_len > 18 and not quotes:
        scores["narrative"] += 0.25
        signals["narrative"].append(f"avg sentence {avg_sentence_len:.1f} words")

    # Conversational: short + casual markers + informal.
    conv = len(_CONVERSATIONAL_MARKERS.findall(text))
    if conv:
        scores["conversational"] += min(0.6, 0.2 + 0.1 * conv)
        signals["conversational"].append(f"{conv} casual marker(s)")
    if word_count < 20 and "?" in text:
        scores["conversational"] += 0.2
        signals["conversational"].append("short question")
    if word_count < 50 and not emotions and not tech and not narr:
        scores["conversational"] += 0.15
        signals["conversational"].append("short and generic")

    # If nothing scored, fall back to conversational so the UI always
    # has something to suggest.
    if all(v == 0 for v in scores.values()):
        scores["conversational"] = 0.1
        signals["conversational"].append("default fallback")

    # Cap scores at 1.0.
    for k in scores:
        scores[k] = min(1.0, scores[k])

    ranked = sorted(
        (
            ContextScore(context=c, score=scores[c], signals=signals[c])
            for c in CONTEXTS
        ),
        key=lambda s: s.score,
        reverse=True,
    )
    return ranked


# ---------------------------------------------------------------------------
# Profile ranking
# ---------------------------------------------------------------------------


# Which provider generally excels at each context. The numeric value is a
# base affinity score; preference-history boosts layer on top.
#
# These are editorial defaults — we expose them in the response payload so
# a future admin UI can tune them, and the test suite pins the numbers so
# ranking changes are reviewable.
_PROVIDER_CONTEXT_AFFINITY: dict[Context, dict[str, float]] = {
    "conversational": {"kokoro": 0.9, "piper": 0.7, "azure_speech": 0.6, "elevenlabs": 0.75},
    "narrative":      {"coqui_xtts": 0.85, "elevenlabs": 0.85, "styletts2": 0.8, "azure_speech": 0.7},
    "emotional":      {"elevenlabs": 0.95, "azure_speech": 0.85, "styletts2": 0.75, "coqui_xtts": 0.6},
    "technical":      {"azure_speech": 0.9, "kokoro": 0.75, "piper": 0.7, "elevenlabs": 0.6},
    "dialogue":       {"dia2": 0.95, "dia": 0.85, "elevenlabs": 0.7, "coqui_xtts": 0.6},
    "long_form":      {"coqui_xtts": 0.9, "elevenlabs": 0.8, "styletts2": 0.8, "azure_speech": 0.7},
}


@dataclass
class ProfileRecommendation:
    """A single ranked suggestion surfaced to the user."""

    profile_id: str
    profile_name: str
    provider_name: str
    voice_id: str | None
    score: float  # 0..1 — blended score
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RoutingRecommendation:
    """Top-level payload — the classification + the ranked profiles."""

    text_excerpt: str  # first ~120 chars, safe for UI
    top_context: Context
    context_scores: list[ContextScore]
    recommendations: list[ProfileRecommendation]

    def to_dict(self) -> dict:
        return {
            "text_excerpt": self.text_excerpt,
            "top_context": self.top_context,
            "context_scores": [c.to_dict() for c in self.context_scores],
            "recommendations": [r.to_dict() for r in self.recommendations],
        }


async def _load_preference_biases(
    db: AsyncSession,
    profile_ids: Iterable[str],
) -> dict[str, float]:
    """Return per-profile bias ∈ [−0.2, +0.2] derived from SL-26 preference summary.

    Profiles the user has thumbs-up'd are nudged up; thumbs-down nudges
    down. Missing preference rows contribute 0.
    """
    # Lazy import so SL-30 loads cleanly even on installs where the
    # SL-26 migration hasn't been applied (older tests, dev envs).
    try:
        from app.models.preference_summary import PreferenceSummary  # type: ignore[import-not-found]
    except ImportError:
        return {}

    ids = [p for p in profile_ids if p]
    if not ids:
        return {}

    try:
        rows = (
            await db.execute(
                select(PreferenceSummary).where(PreferenceSummary.profile_id.in_(ids))
            )
        ).scalars().all()
    except Exception as exc:
        logger.debug("preference_summary_lookup_skipped", error=str(exc))
        return {}

    biases: dict[str, float] = {}
    for row in rows:
        payload: dict = {}
        raw = getattr(row, "summary_json", None)
        if not raw:
            continue
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            continue
        up = float(payload.get("up", 0) or 0)
        down = float(payload.get("down", 0) or 0)
        total = up + down
        if total <= 0:
            continue
        # Balance in [-1, 1]; attenuate to ±0.2 so base affinity dominates.
        balance = (up - down) / total
        biases[row.profile_id] = max(-0.2, min(0.2, balance * 0.2))
    return biases


def rank_profiles(
    profiles: list[VoiceProfile],
    top_context: Context,
    *,
    preference_biases: dict[str, float] | None = None,
    affinity: dict[Context, dict[str, float]] | None = None,
    limit: int = 3,
) -> list[ProfileRecommendation]:
    """Rank ``profiles`` for a classified context and return the top ``limit``.

    Base score = provider affinity (0..1). Optional preference bias is added
    in ±0.2. Ties break by profile name ascending so the output is stable.
    """
    table = affinity or _PROVIDER_CONTEXT_AFFINITY
    context_affinity = table.get(top_context, {})
    scored: list[ProfileRecommendation] = []

    for p in profiles:
        base = context_affinity.get(p.provider_name, 0.4)  # default mid-value
        reasons = [
            f"{p.provider_name} affinity for '{top_context}' = {base:.2f}",
        ]
        bias = (preference_biases or {}).get(p.id, 0.0)
        if bias:
            reasons.append(f"preference bias {bias:+.2f}")
        final = max(0.0, min(1.0, base + bias))
        scored.append(ProfileRecommendation(
            profile_id=p.id,
            profile_name=p.name,
            provider_name=p.provider_name,
            voice_id=p.voice_id,
            score=round(final, 3),
            reasons=reasons,
        ))

    scored.sort(key=lambda r: (-r.score, r.profile_name.lower()))
    return scored[:limit]


async def recommend_route(
    db: AsyncSession,
    text: str,
    *,
    limit: int = 3,
) -> RoutingRecommendation:
    """End-to-end: classify ``text`` then rank the user's profiles.

    Only considers profiles whose status is 'ready' (trained or library-voiced);
    unreadied profiles aren't usable for synthesis.
    """
    rows = (
        await db.execute(
            select(VoiceProfile).where(VoiceProfile.status == "ready")
        )
    ).scalars().all()

    context_scores = classify_text(text)
    top = context_scores[0].context

    biases = await _load_preference_biases(db, [p.id for p in rows])
    recs = rank_profiles(
        list(rows), top, preference_biases=biases, limit=limit
    )

    excerpt = (text or "").strip().replace("\n", " ")
    if len(excerpt) > 120:
        excerpt = excerpt[:117] + "…"

    logger.info(
        "context_router_recommendation",
        top_context=top,
        profile_count=len(rows),
        returned=len(recs),
    )

    return RoutingRecommendation(
        text_excerpt=excerpt,
        top_context=top,
        context_scores=context_scores,
        recommendations=recs,
    )
