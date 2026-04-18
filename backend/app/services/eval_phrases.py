"""Held-out evaluation phrases used by the SL-27 regression detector.

Ten phonetically balanced English sentences (pangrams + common carrier
phrases) that cover a broad range of vowels, consonants, and prosody.  The
set is intentionally short so running Whisper on each phrase stays cheap
enough to evaluate every new ModelVersion synchronously.
"""

from __future__ import annotations

EVAL_PHRASES: list[str] = [
    "The quick brown fox jumps over the lazy dog.",
    "She sells sea shells by the sea shore.",
    "How much wood would a woodchuck chuck if a woodchuck could chuck wood.",
    "Peter Piper picked a peck of pickled peppers.",
    "The five boxing wizards jump quickly.",
    "Pack my box with five dozen liquor jugs.",
    "Sphinx of black quartz, judge my vow.",
    "A journey of a thousand miles begins with a single step.",
    "To be or not to be, that is the question.",
    "All that glitters is not gold.",
]


def get_eval_phrases() -> list[str]:
    """Return the canonical evaluation phrase list (defensive copy)."""
    return list(EVAL_PHRASES)
