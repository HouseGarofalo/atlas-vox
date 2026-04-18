"""VQ-37 — prosody / emotion visual preview.

Given a chunk of text, predict a per-word pitch contour, energy curve, and
duration footprint the TTS provider is likely to produce. The v1 is a
transparent heuristic — no acoustic model dependency — so it ships on
every install. Subsequent versions can swap the predictor for a small
ONNX model without changing the API shape.

Signals used:
    Pitch:
      - Baseline 0.
      - Sentence-position rise/fall: statements decline 0.08 toward the
        final word; questions rise 0.15. Exclamations get a mid-clause
        bump.
      - Stress: ALL-CAPS words get +0.25; *emphasised* / __strong__ words
        get +0.18; parenthetical or quoted-aside words get −0.15.
      - Long content words (>= 2 syllables) get +0.05 — stressed syllables
        are higher-pitched on average.
    Energy:
      - Baseline 0.5.
      - Emphasised / shouted words +0.25; whispered / parenthetical −0.25.
      - Exclamations boost the nearby 3 words by +0.1.
    Duration:
      - Syllable count × base rate (50ms per syllable).
      - Longer pause after commas (+120ms), semicolons/colons (+200ms),
        sentence-enders (+350ms).
      - Emphasised words +15% duration; trailing-ellipsis +250ms.
    Emotion overlay (optional): see ``_apply_emotion``. Simple additive
    offsets tuned to match the Azure mstts:express-as style set.

The preview also emits an SSML string for the currently-selected
emphasis levels so the frontend can feed it straight into synthesize().
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Iterable

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ProsodyWord:
    """One word's predicted prosody row."""

    index: int
    text: str
    pitch: float  # normalized to roughly [-1, 1]
    energy: float  # normalized to [0, 1]
    duration_ms: int
    syllables: int
    is_sentence_end: bool = False
    emphasis: str = "normal"  # normal | reduced | strong — user-editable
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProsodyPreview:
    """The full payload returned by :func:`build_prosody_preview`."""

    text: str
    words: list[ProsodyWord] = field(default_factory=list)
    sentence_count: int = 0
    total_duration_ms: int = 0
    pitch_range: tuple[float, float] = (0.0, 0.0)
    ssml: str = ""
    emotion: str | None = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "words": [w.to_dict() for w in self.words],
            "sentence_count": self.sentence_count,
            "total_duration_ms": self.total_duration_ms,
            "pitch_min": self.pitch_range[0],
            "pitch_max": self.pitch_range[1],
            "ssml": self.ssml,
            "emotion": self.emotion,
        }


# ---------------------------------------------------------------------------
# Tokenisation + syllable counting
# ---------------------------------------------------------------------------

# Matches a word-ish token including internal apostrophes. We track
# trailing punctuation separately so sentence-position logic is clean.
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’]*")
_SENTENCE_ENDERS = set(".!?")
_VOWEL_RUN = re.compile(r"[aeiouyAEIOUY]+")


def _syllables(word: str) -> int:
    """Cheap syllable estimator — good enough for prosody weighting.

    Counts vowel groups; subtracts a syllable for a silent trailing ``e``.
    Always returns at least 1 so single-letter words still register.
    """
    stripped = word.strip("'’")
    if not stripped:
        return 1
    groups = len(_VOWEL_RUN.findall(stripped))
    # Silent-e heuristic: words ending in 'e' where the vowel count > 1
    # usually drop one (e.g. "make", "bike"). Skip for very short words
    # ("the", "be") where the 'e' IS the vowel.
    if (
        groups > 1
        and stripped.lower().endswith("e")
        and not stripped.lower().endswith(("le", "ee", "ie", "oe", "ue"))
    ):
        groups -= 1
    return max(1, groups)


def _tokenize(text: str) -> list[tuple[str, str]]:
    """Return a list of (word, trailing_punct) tuples, preserving order."""
    tokens: list[tuple[str, str]] = []
    i = 0
    n = len(text)
    while i < n:
        m = _WORD_RE.match(text, i)
        if not m:
            i += 1
            continue
        word = m.group(0)
        i = m.end()
        # Collect trailing punctuation up to the next word or whitespace run.
        punct_start = i
        while i < n and text[i] not in " \t\n\r":
            if _WORD_RE.match(text, i):
                break
            i += 1
        tokens.append((word, text[punct_start:i]))
    return tokens


# ---------------------------------------------------------------------------
# Emphasis detection
# ---------------------------------------------------------------------------

_EMPHASIS_MARKUP = re.compile(r"\*\*([^*]+)\*\*|__([^_]+)__|\*([^*]+)\*")


def _precompute_emphasis_ranges(text: str) -> set[tuple[int, int]]:
    """Return (start, end) character ranges covered by markdown-style emphasis."""
    ranges: set[tuple[int, int]] = set()
    for m in _EMPHASIS_MARKUP.finditer(text):
        ranges.add(m.span())
    return ranges


def _emphasis_level(
    word: str,
    char_start: int,
    ranges: set[tuple[int, int]],
) -> str:
    """Classify a word's emphasis from markup + case shape."""
    if word.isupper() and len(word) > 1:
        return "strong"
    for a, b in ranges:
        if a <= char_start < b:
            return "strong"
    return "normal"


# ---------------------------------------------------------------------------
# Emotion overlay
# ---------------------------------------------------------------------------


# Emotion → (pitch_shift, energy_shift, duration_multiplier). Matches the
# qualitative shape of the Azure mstts:express-as catalogue so users see
# an intuitive preview before they even pick a provider.
_EMOTION_OVERLAYS: dict[str, tuple[float, float, float]] = {
    "cheerful":     (0.15, 0.12, 0.95),
    "excited":      (0.20, 0.20, 0.92),
    "sad":         (-0.18, -0.15, 1.12),
    "angry":        (0.05, 0.28, 0.98),
    "hopeful":      (0.10, 0.08, 0.98),
    "whispering":  (-0.10, -0.35, 1.05),
    "shouting":     (0.18, 0.35, 0.92),
    "calm":        (-0.05, -0.08, 1.05),
    "gentle":      (-0.05, -0.10, 1.05),
    "serious":     (-0.10, 0.00, 1.00),
    "terrified":    (0.25, 0.15, 0.95),
    "neutral":      (0.00, 0.00, 1.00),
}


def _apply_emotion(word: ProsodyWord, shift: tuple[float, float, float]) -> None:
    p, e, d = shift
    word.pitch += p
    word.energy = max(0.0, min(1.0, word.energy + e))
    word.duration_ms = max(30, int(word.duration_ms * d))


# ---------------------------------------------------------------------------
# Main analyser
# ---------------------------------------------------------------------------


def build_prosody_preview(
    text: str,
    *,
    emotion: str | None = None,
    emphasis_overrides: dict[int, str] | None = None,
) -> ProsodyPreview:
    """Build the full prosody preview for ``text``.

    Parameters
    ----------
    text:
        The input. Both plain text and simple markdown-style emphasis
        (``*italic*``, ``**bold**``, ``__strong__``) are recognised.
    emotion:
        Optional emotion label from the Azure style set. Applies a uniform
        offset across every word. Unknown emotions are ignored.
    emphasis_overrides:
        Optional map of word-index → ``"reduced"|"normal"|"strong"``.
        Overrides dominate the heuristic classification so the frontend
        can feed user-edited state straight back in.
    """
    emphasis_overrides = emphasis_overrides or {}
    tokens = _tokenize(text)
    emphasis_ranges = _precompute_emphasis_ranges(text)

    # Build a char-index map so we can test whether each word lies inside
    # a markdown emphasis span.
    word_char_positions: list[int] = []
    cursor = 0
    for word, _trailing in tokens:
        idx = text.find(word, cursor)
        word_char_positions.append(idx)
        cursor = max(cursor + 1, idx + len(word))

    # Sentence-boundary pass — for each token, determine whether it's the
    # last token in its sentence AND the sentence type.
    sentence_ends: list[bool] = [False] * len(tokens)
    sentence_types: list[str] = ["statement"] * len(tokens)  # statement | question | exclaim
    current_type = "statement"
    last_word_in_sentence = -1
    sentence_count = 0
    for i, (_word, trailing) in enumerate(tokens):
        # Does this token's trailing punctuation contain a sentence ender?
        if any(ch in _SENTENCE_ENDERS for ch in trailing):
            sentence_ends[i] = True
            sentence_count += 1
            if "?" in trailing:
                current_type = "question"
            elif "!" in trailing:
                current_type = "exclaim"
            else:
                current_type = "statement"
            # Propagate sentence_type backward to the start of this sentence.
            start = last_word_in_sentence + 1
            for j in range(start, i + 1):
                sentence_types[j] = current_type
            last_word_in_sentence = i

    # Any trailing words without an ender still count as one sentence.
    if last_word_in_sentence < len(tokens) - 1 and tokens:
        sentence_count += 1
        for j in range(last_word_in_sentence + 1, len(tokens)):
            sentence_types[j] = "statement"

    # Second pass — compute features per word.
    words: list[ProsodyWord] = []
    # Sentence boundaries: for rise/fall math we need "position within sentence".
    sentence_start = 0
    for i, (word, trailing) in enumerate(tokens):
        if i == 0 or sentence_ends[i - 1]:
            sentence_start = i
        # Sentence length (inclusive).
        next_end = next(
            (j for j in range(i, len(tokens)) if sentence_ends[j]),
            len(tokens) - 1,
        )
        sent_len = max(1, next_end - sentence_start + 1)
        pos_in_sent = i - sentence_start
        progress = pos_in_sent / max(1, sent_len - 1) if sent_len > 1 else 1.0

        syl = _syllables(word)
        char_start = word_char_positions[i]
        detected_emphasis = _emphasis_level(word, char_start, emphasis_ranges)
        emphasis = emphasis_overrides.get(i, detected_emphasis)

        # ---- Pitch ----
        pitch = 0.0
        reasons: list[str] = []
        sent_type = sentence_types[i]
        if sent_type == "question":
            # Rising intonation toward the end.
            pitch += 0.15 * progress
            if progress > 0.8:
                reasons.append("question rise")
        elif sent_type == "exclaim":
            pitch += 0.10 * progress
            if progress > 0.5:
                reasons.append("exclamation boost")
        else:
            # Statements drift down.
            pitch -= 0.08 * progress
            if progress > 0.8:
                reasons.append("declarative fall")

        if emphasis == "strong":
            pitch += 0.25
            reasons.append("emphasised (+pitch)")
        elif emphasis == "reduced":
            pitch -= 0.15
            reasons.append("reduced (−pitch)")

        if syl >= 2:
            pitch += 0.05
            reasons.append(f"{syl} syllables")

        # ---- Energy ----
        energy = 0.5
        if emphasis == "strong":
            energy += 0.25
        elif emphasis == "reduced":
            energy -= 0.25
        if sent_type == "exclaim":
            energy += 0.10
        energy = max(0.0, min(1.0, energy))

        # ---- Duration ----
        base_per_syl = 55
        duration_ms = syl * base_per_syl
        if "," in trailing:
            duration_ms += 120
            reasons.append("comma pause")
        if any(ch in trailing for ch in ";:"):
            duration_ms += 200
        if any(ch in trailing for ch in _SENTENCE_ENDERS):
            duration_ms += 350
            reasons.append("sentence pause")
        if "..." in trailing or "…" in trailing:
            duration_ms += 250
        if emphasis == "strong":
            duration_ms = int(duration_ms * 1.15)

        words.append(ProsodyWord(
            index=i,
            text=word,
            pitch=round(pitch, 3),
            energy=round(energy, 3),
            duration_ms=duration_ms,
            syllables=syl,
            is_sentence_end=sentence_ends[i],
            emphasis=emphasis,
            reasons=reasons,
        ))

    # Apply emotion overlay.
    if emotion and emotion in _EMOTION_OVERLAYS:
        shift = _EMOTION_OVERLAYS[emotion]
        for w in words:
            _apply_emotion(w, shift)

    # Clamp pitch post-overlay and compute summary stats.
    if words:
        for w in words:
            w.pitch = round(max(-1.0, min(1.0, w.pitch)), 3)
        pitch_min = min(w.pitch for w in words)
        pitch_max = max(w.pitch for w in words)
    else:
        pitch_min = pitch_max = 0.0

    ssml = _build_ssml(text, words, emotion=emotion)
    total_ms = sum(w.duration_ms for w in words)

    logger.info(
        "prosody_preview_built",
        word_count=len(words),
        sentence_count=sentence_count,
        emotion=emotion,
        total_duration_ms=total_ms,
    )

    return ProsodyPreview(
        text=text,
        words=words,
        sentence_count=sentence_count,
        total_duration_ms=total_ms,
        pitch_range=(pitch_min, pitch_max),
        ssml=ssml,
        emotion=emotion,
    )


# ---------------------------------------------------------------------------
# SSML emission
# ---------------------------------------------------------------------------


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _build_ssml(text: str, words: Iterable[ProsodyWord], *, emotion: str | None) -> str:
    """Produce SSML with <emphasis> tags around user-adjusted words.

    We intentionally only emit markup for non-default emphasis so the
    output stays readable. When no words are tagged and no emotion is
    applied, we return a minimal ``<speak>`` wrapper with the raw text.
    """
    parts: list[str] = []
    for w in words:
        piece = _escape(w.text)
        if w.emphasis == "strong":
            piece = f'<emphasis level="strong">{piece}</emphasis>'
        elif w.emphasis == "reduced":
            piece = f'<emphasis level="reduced">{piece}</emphasis>'
        parts.append(piece)
    body = " ".join(parts) if parts else _escape(text)
    if emotion and emotion in _EMOTION_OVERLAYS:
        body = f'<mstts:express-as style="{_escape(emotion)}">{body}</mstts:express-as>'
    return (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="en-US">'
        f"{body}"
        "</speak>"
    )


def supported_emotions() -> list[str]:
    """Return the ordered list of emotions the preview understands."""
    return list(_EMOTION_OVERLAYS.keys())
