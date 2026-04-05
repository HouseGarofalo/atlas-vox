"""Word boundary estimation using Whisper timestamps.

Provides word-level timing data for providers that don't natively support
word boundaries (all except Azure Speech). Uses faster-whisper's
word_timestamps feature to estimate timing from synthesized audio.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class WordBoundary:
    text: str
    offset_ms: int
    duration_ms: int
    word_index: int


def _estimate_sync(audio_path: Path) -> list[WordBoundary]:
    """Synchronous word boundary estimation (runs in executor)."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        logger.warning("word_boundary_estimation_unavailable", reason="faster-whisper not installed")
        return []

    # Use tiny model for speed — we only need word timing, not accuracy
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    segments, _info = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        language="en",
    )

    boundaries: list[WordBoundary] = []
    idx = 0
    for segment in segments:
        if not segment.words:
            continue
        for word in segment.words:
            boundaries.append(WordBoundary(
                text=word.word.strip(),
                offset_ms=int(word.start * 1000),
                duration_ms=int((word.end - word.start) * 1000),
                word_index=idx,
            ))
            idx += 1

    return boundaries


async def estimate_word_boundaries(audio_path: Path) -> list[WordBoundary]:
    """Estimate word boundaries from synthesized audio.

    Args:
        audio_path: Path to the synthesized audio file.

    Returns:
        List of word boundaries with timing data. Empty list if
        faster-whisper is not installed.
    """
    if not audio_path.exists():
        return []

    logger.info("word_boundary_estimation_start", path=str(audio_path))
    loop = asyncio.get_event_loop()
    boundaries = await loop.run_in_executor(None, _estimate_sync, audio_path)
    logger.info("word_boundary_estimation_complete", word_count=len(boundaries))
    return boundaries
