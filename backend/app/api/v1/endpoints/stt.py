"""Speech-to-Text endpoints — streaming and batch.

Endpoints
---------
POST /stt/transcribe
    Non-streaming transcription.  Returns the full transcript, word-level
    timestamps, and the detected language.

POST /stt/stream
    Server-Sent Events endpoint that emits `language_detected`, `partial`,
    `final`, and `done` events as transcription progresses.

Both endpoints accept either ``multipart/form-data`` with an ``audio`` file
field, or a raw ``application/octet-stream`` body.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.dependencies import CurrentUser

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/stt", tags=["stt"])

# Conservative upload cap — whisper is happy with long files but we don't
# want to DOS the box.
MAX_STT_BYTES = 50 * 1024 * 1024  # 50MB

ALLOWED_AUDIO_SUFFIXES = {
    "wav",
    "mp3",
    "flac",
    "ogg",
    "m4a",
    "webm",
    "aac",
    "mp4",
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class WordTimestampOut(BaseModel):
    word: str
    start: float
    end: float
    probability: float | None = None


class SegmentOut(BaseModel):
    start: float
    end: float
    text: str
    words: list[WordTimestampOut] = []


class TranscribeResponse(BaseModel):
    text: str
    language: str
    language_probability: float | None = None
    segments: list[SegmentOut] = []
    words: list[WordTimestampOut] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tmp_dir() -> Path:
    d = Path(settings.storage_path) / "stt"
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _persist_request_audio(request: Request) -> Path:
    """Write the request body (multipart or raw) to disk.  Returns the path.

    Raises HTTPException on validation errors.
    """
    ctype = (request.headers.get("content-type") or "").lower()

    if "multipart/form-data" in ctype:
        form = await request.form()
        upload = form.get("audio")
        if upload is None or not hasattr(upload, "read") or not hasattr(upload, "filename"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'audio' field in multipart payload",
            )
        filename = getattr(upload, "filename", None) or "upload.bin"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        if ext not in ALLOWED_AUDIO_SUFFIXES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported audio format: .{ext}",
            )
        content = await upload.read()
    else:
        content = await request.body()
        ext = "bin"

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio payload",
        )
    if len(content) > MAX_STT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio exceeds {MAX_STT_BYTES // (1024 * 1024)}MB limit",
        )

    out = _tmp_dir() / f"stt_{uuid.uuid4().hex[:16]}.{ext}"
    out.write_bytes(content)
    logger.info("stt_audio_persisted", path=str(out), bytes=len(content))
    return out


def _sse(event: str, data: dict | str) -> bytes:
    """Format an SSE event chunk."""
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_endpoint(
    request: Request,
    user: CurrentUser,
    language: str | None = Query(
        None, description="ISO code (en, es, …). Omit to auto-detect."
    ),
) -> TranscribeResponse:
    """Synchronous transcription with word-level timestamps."""
    from app.services.whisper_transcriber import transcribe_detailed

    audio_path = await _persist_request_audio(request)

    try:
        result = await transcribe_detailed(audio_path, language=language)
    except RuntimeError as exc:
        logger.warning("stt_backend_missing", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    finally:
        audio_path.unlink(missing_ok=True)

    payload = result.to_dict()
    logger.info(
        "stt_transcribe_ok",
        chars=len(payload["text"]),
        language=payload["language"],
        segments=len(payload["segments"]),
    )
    return TranscribeResponse.model_validate(payload)


@router.post("/stream")
async def stream_endpoint(
    request: Request,
    user: CurrentUser,
    language: str | None = Query(
        None, description="ISO code. Omit to auto-detect."
    ),
) -> StreamingResponse:
    """Stream whisper transcription as SSE events.

    Events emitted (in order):

    * ``language_detected`` — fired once the model picks a language.
    * ``partial``           — one per transcribed segment.
    * ``final``             — aggregated transcript + segment list.
    * ``done``              — end-of-stream marker.
    """
    from app.services.whisper_transcriber import stream_transcribe

    audio_path = await _persist_request_audio(request)

    async def event_stream():
        try:
            async for event in stream_transcribe(audio_path, language=language):
                etype = event.get("type", "partial")
                # Normalise event names expected by the acceptance criteria.
                if etype == "language_detected":
                    yield _sse("language_detected", event)
                elif etype == "partial":
                    yield _sse("partial", event)
                elif etype == "final":
                    yield _sse("final", event)
                elif etype == "error":
                    yield _sse("error", event)
                else:
                    yield _sse(etype, event)
            yield _sse("done", {"status": "complete"})
        except RuntimeError as exc:
            logger.warning("stt_stream_backend_missing", error=str(exc))
            yield _sse("error", {"message": str(exc)})
            yield _sse("done", {"status": "error"})
        finally:
            audio_path.unlink(missing_ok=True)

    logger.info("stt_stream_start", path=str(audio_path))
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
