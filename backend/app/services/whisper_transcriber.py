"""Whisper-based transcription fallback for providers without native STT.

Uses OpenAI's whisper model (via the `openai-whisper` package if installed,
or falls back to `faster-whisper` for better performance). Provides
provider-agnostic transcription for the Training Studio and sample analysis.

The module also exposes richer helpers used by the streaming STT endpoint:

* :func:`transcribe_detailed` — returns word timestamps + detected language.
* :func:`stream_transcribe` — yields partial / final segment events as they
  become available (faster-whisper only; openai-whisper runs sequentially).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Cache the model to avoid reloading on every call
_model = None
_backend: str | None = None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class WordTimestamp:
    """A single word with its timing information."""

    word: str
    start: float
    end: float
    probability: float | None = None

    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "start": self.start,
            "end": self.end,
            "probability": self.probability,
        }


@dataclass
class TranscriptSegment:
    """A segment of transcript returned by whisper."""

    start: float
    end: float
    text: str
    words: list[WordTimestamp] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "words": [w.to_dict() for w in self.words],
        }


@dataclass
class TranscriptResult:
    """Aggregate transcript with language info and word timings."""

    text: str
    language: str
    language_probability: float | None = None
    segments: list[TranscriptSegment] = field(default_factory=list)

    @property
    def words(self) -> list[WordTimestamp]:
        return [w for seg in self.segments for w in seg.words]

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "language": self.language,
            "language_probability": self.language_probability,
            "segments": [s.to_dict() for s in self.segments],
            "words": [w.to_dict() for w in self.words],
        }


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Sync helpers (all called from an executor)
# ---------------------------------------------------------------------------

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


def _transcribe_detailed_sync(
    audio_path: Path,
    language: str | None = None,
) -> TranscriptResult:
    """Synchronous detailed transcription with word timestamps + language detect."""
    model, backend = _load_model()

    if backend == "faster-whisper":
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=True,
        )
        segments: list[TranscriptSegment] = []
        for seg in segments_iter:
            words = [
                WordTimestamp(
                    word=getattr(w, "word", "").strip(),
                    start=float(getattr(w, "start", 0.0) or 0.0),
                    end=float(getattr(w, "end", 0.0) or 0.0),
                    probability=(
                        float(getattr(w, "probability"))
                        if getattr(w, "probability", None) is not None
                        else None
                    ),
                )
                for w in (getattr(seg, "words", None) or [])
            ]
            segments.append(
                TranscriptSegment(
                    start=float(seg.start),
                    end=float(seg.end),
                    text=seg.text.strip(),
                    words=words,
                )
            )
        text = " ".join(s.text for s in segments).strip()
        return TranscriptResult(
            text=text,
            language=getattr(info, "language", "en") or "en",
            language_probability=float(getattr(info, "language_probability", 0.0) or 0.0),
            segments=segments,
        )

    # openai-whisper fallback
    import whisper  # noqa: F401

    result = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
    )
    segments = []
    for seg in result.get("segments", []):
        words = [
            WordTimestamp(
                word=str(w.get("word", "")).strip(),
                start=float(w.get("start", 0.0)),
                end=float(w.get("end", 0.0)),
                probability=(
                    float(w["probability"]) if w.get("probability") is not None else None
                ),
            )
            for w in (seg.get("words") or [])
        ]
        segments.append(
            TranscriptSegment(
                start=float(seg.get("start", 0.0)),
                end=float(seg.get("end", 0.0)),
                text=str(seg.get("text", "")).strip(),
                words=words,
            )
        )
    return TranscriptResult(
        text=str(result.get("text", "")).strip(),
        language=str(result.get("language") or language or "en"),
        language_probability=None,
        segments=segments,
    )


# ---------------------------------------------------------------------------
# Async API
# ---------------------------------------------------------------------------

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


async def transcribe_detailed(
    audio_path: Path,
    language: str | None = None,
) -> TranscriptResult:
    """Transcribe with word-level timestamps and auto language detection."""
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    logger.info("whisper_detailed_start", path=str(audio_path), language=language)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, _transcribe_detailed_sync, audio_path, language
    )
    logger.info(
        "whisper_detailed_complete",
        path=str(audio_path),
        text_length=len(result.text),
        segments=len(result.segments),
        language=result.language,
    )
    return result


async def stream_transcribe(
    audio_path: Path,
    language: str | None = None,
) -> AsyncIterator[dict]:
    """Yield streaming events as segments become available.

    Event shape::

        {"type": "language_detected", "language": "en", "probability": 0.99}
        {"type": "partial", "segment": {...}}
        {"type": "final", "text": "...", "language": "en", "segments": [...]}

    With openai-whisper, transcription is not incremental, so only a single
    ``final`` event (preceded by ``language_detected``) is emitted.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    _load_model()  # raise early if unavailable
    _, backend = _model, _backend

    if backend == "faster-whisper":
        # Run generator in a worker thread and ferry events back.
        queue: asyncio.Queue = asyncio.Queue()
        sentinel = object()

        def _producer() -> None:
            try:
                model, _ = _load_model()
                segments_iter, info = model.transcribe(
                    str(audio_path),
                    language=language,
                    word_timestamps=True,
                )
                queue.put_nowait(
                    {
                        "type": "language_detected",
                        "language": getattr(info, "language", "en") or "en",
                        "probability": float(
                            getattr(info, "language_probability", 0.0) or 0.0
                        ),
                    }
                )
                final_segments: list[TranscriptSegment] = []
                for seg in segments_iter:
                    words = [
                        WordTimestamp(
                            word=getattr(w, "word", "").strip(),
                            start=float(getattr(w, "start", 0.0) or 0.0),
                            end=float(getattr(w, "end", 0.0) or 0.0),
                            probability=(
                                float(getattr(w, "probability"))
                                if getattr(w, "probability", None) is not None
                                else None
                            ),
                        )
                        for w in (getattr(seg, "words", None) or [])
                    ]
                    ts = TranscriptSegment(
                        start=float(seg.start),
                        end=float(seg.end),
                        text=seg.text.strip(),
                        words=words,
                    )
                    final_segments.append(ts)
                    queue.put_nowait({"type": "partial", "segment": ts.to_dict()})
                result_text = " ".join(s.text for s in final_segments).strip()
                queue.put_nowait(
                    {
                        "type": "final",
                        "text": result_text,
                        "language": getattr(info, "language", "en") or "en",
                        "segments": [s.to_dict() for s in final_segments],
                    }
                )
            except Exception as exc:  # pragma: no cover - defensive
                queue.put_nowait({"type": "error", "message": str(exc)})
            finally:
                queue.put_nowait(sentinel)

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _producer)

        while True:
            event = await queue.get()
            if event is sentinel:
                break
            yield event
        return

    # openai-whisper — single shot.
    result = await transcribe_detailed(audio_path, language=language)
    yield {
        "type": "language_detected",
        "language": result.language,
        "probability": result.language_probability,
    }
    for seg in result.segments:
        yield {"type": "partial", "segment": seg.to_dict()}
    yield {
        "type": "final",
        "text": result.text,
        "language": result.language,
        "segments": [s.to_dict() for s in result.segments],
    }


async def is_available() -> bool:
    """Check if any whisper backend is installed."""
    try:
        _load_model()
        return True
    except RuntimeError:
        return False
