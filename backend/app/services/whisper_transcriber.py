"""Whisper-based transcription fallback for providers without native STT.

Uses OpenAI's whisper model (via the `openai-whisper` package if installed,
or falls back to `faster-whisper` for better performance). Provides
provider-agnostic transcription for the Training Studio and sample analysis.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Cache the model to avoid reloading on every call
_model = None
_backend: str | None = None


def _load_model():
    """Lazily load a whisper model, preferring faster-whisper over openai-whisper."""
    global _model, _backend

    if _model is not None:
        return _model, _backend

    # Try faster-whisper first (faster, lower memory)
    try:
        from faster_whisper import WhisperModel
        _model = WhisperModel("base", device="cpu", compute_type="int8")
        _backend = "faster-whisper"
        logger.info("whisper_loaded", backend="faster-whisper", model="base")
        return _model, _backend
    except ImportError:
        pass

    # Fall back to openai-whisper
    try:
        import whisper
        _model = whisper.load_model("base")
        _backend = "openai-whisper"
        logger.info("whisper_loaded", backend="openai-whisper", model="base")
        return _model, _backend
    except ImportError:
        pass

    raise RuntimeError(
        "No whisper backend available. Install either 'faster-whisper' or 'openai-whisper'."
    )


def _transcribe_sync(audio_path: Path, language: str = "en") -> str:
    """Synchronous transcription (runs in executor)."""
    model, backend = _load_model()

    if backend == "faster-whisper":
        segments, _info = model.transcribe(str(audio_path), language=language)
        return " ".join(seg.text.strip() for seg in segments)
    else:
        # openai-whisper
        result = model.transcribe(str(audio_path), language=language)
        return result["text"].strip()


async def transcribe(audio_path: Path, language: str = "en") -> str:
    """Transcribe an audio file using Whisper.

    Args:
        audio_path: Path to the audio file (WAV, MP3, etc.)
        language: ISO language code (default "en").

    Returns:
        Transcribed text.

    Raises:
        RuntimeError: If no whisper backend is installed.
        FileNotFoundError: If the audio file doesn't exist.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    logger.info("whisper_transcribe_start", path=str(audio_path), language=language)

    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, _transcribe_sync, audio_path, language)

    logger.info("whisper_transcribe_complete", path=str(audio_path), text_length=len(text))
    return text


async def is_available() -> bool:
    """Check if any whisper backend is installed."""
    try:
        _load_model()
        return True
    except RuntimeError:
        return False
