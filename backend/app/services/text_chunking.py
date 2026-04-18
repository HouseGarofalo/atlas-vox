"""Text-chunking service — provider-aware length splitting for TTS input.

Extracted from ``synthesis_service`` (P2-17). Keeps the orchestrator thin by
moving pure text-processing logic into a dedicated module.
"""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger(__name__)

# Provider-specific character limits for text chunking.
# Tuned so each chunk stays within the provider's comfortable input size and
# does not degrade quality (long clips drift / run out of context).
PROVIDER_CHAR_LIMITS: dict[str, int] = {
    "elevenlabs": 5000,
    "azure_speech": 3000,  # Conservative; Azure handles ~10 min of audio
    "kokoro": 2000,
    "coqui_xtts": 1500,
    "piper": 2000,
    "styletts2": 1000,
    "cosyvoice": 1500,
    "dia": 1000,
    "dia2": 1000,
}

CHUNK_MAX_CHARS_DEFAULT = 1500


def split_text(text: str, max_chars: int = CHUNK_MAX_CHARS_DEFAULT) -> list[str]:
    """Split long text at paragraph/sentence boundaries.

    Respects a configurable ``max_chars`` limit. First tries to split on
    paragraph breaks (double newline), then falls back to sentence boundaries,
    then word boundaries for very long sentences.
    """
    if len(text) <= max_chars:
        return [text]

    logger.debug("text_chunked", text_length=len(text), max_chars=max_chars)

    chunks: list[str] = []
    current = ""

    # First split on paragraph breaks, then sentence boundaries within each.
    paragraphs = re.split(r"\n\s*\n", text)
    sentences: list[str] = []
    for para in paragraphs:
        para_sentences = re.split(r"(?<=[.!?])\s+", para.strip())
        sentences.extend(para_sentences)

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip() if current else sentence
        else:
            if current:
                chunks.append(current)
            # Handle very long sentences by splitting on words
            if len(sentence) > max_chars:
                words = sentence.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= max_chars:
                        current = f"{current} {word}".strip() if current else word
                    else:
                        if current:
                            chunks.append(current)
                        current = word
            else:
                current = sentence

    if current:
        chunks.append(current)
    return chunks


def chunk_limit_for(provider_name: str) -> int:
    """Return the per-chunk character budget for a provider."""
    return PROVIDER_CHAR_LIMITS.get(provider_name, CHUNK_MAX_CHARS_DEFAULT)
