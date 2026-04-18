"""Synthesis endpoints — single, stream, batch, history, feedback."""

import time
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.core.rate_limit import limiter
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.schemas.synthesis import (
    BatchSynthesisRequest,
    SynthesisRequest,
    SynthesisResponse,
)
from app.services.feedback_service import (
    create_feedback,
    feedback_to_response_dict,
    list_feedback_for_history,
)
from app.services.synthesis_service import (
    batch_synthesize,
    get_history,
    stream_synthesize,
    synthesize,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["synthesis"])


@router.post("/synthesize", response_model=SynthesisResponse)
@limiter.limit("10/minute")
async def synthesize_text(
    request: Request, data: SynthesisRequest, db: DbSession, user: CurrentUser
) -> SynthesisResponse:
    """Synthesize text to speech, return audio URL."""
    logger.info(
        "synthesize_text_called",
        text_length=len(data.text),
        profile_id=data.profile_id,
        preset_id=data.preset_id,
        output_format=data.output_format,
        ssml=data.ssml,
    )
    t_start = time.perf_counter()
    try:
        result = await synthesize(
            db,
            text=data.text,
            profile_id=data.profile_id,
            preset_id=data.preset_id,
            speed=data.speed,
            pitch=data.pitch,
            volume=data.volume,
            output_format=data.output_format,
            ssml=data.ssml,
            include_word_boundaries=data.include_word_boundaries,
            voice_settings=data.voice_settings,
            version_id=data.version_id,
            preprocess=data.preprocess,
        )
        latency_ms = int((time.perf_counter() - t_start) * 1000)
        logger.info(
            "synthesize_text_succeeded",
            profile_id=data.profile_id,
            latency_ms=latency_ms,
        )
        return SynthesisResponse(**result)
    except ValueError as e:
        logger.error(
            "synthesize_text_failed",
            profile_id=data.profile_id,
            text_length=len(data.text),
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/synthesize/stream")
@limiter.limit("10/minute")
async def stream_synthesis(
    request: Request, data: SynthesisRequest, db: DbSession, user: CurrentUser
) -> StreamingResponse:
    """Stream synthesis — chunked transfer encoding for streaming providers."""
    logger.info(
        "stream_synthesis_called",
        text_length=len(data.text),
        profile_id=data.profile_id,
    )
    try:
        audio_stream = stream_synthesize(
            db,
            text=data.text,
            profile_id=data.profile_id,
            speed=data.speed,
            pitch=data.pitch,
            output_format=data.output_format,
        )
        mime_map = {"wav": "audio/wav", "mp3": "audio/mpeg", "ogg": "audio/ogg"}
        media_type = mime_map.get(data.output_format, "audio/wav")
        logger.info("stream_synthesis_started", profile_id=data.profile_id)
        return StreamingResponse(
            audio_stream,
            media_type=media_type,
            headers={"Transfer-Encoding": "chunked"},
        )
    except ValueError as e:
        logger.error(
            "stream_synthesis_failed",
            profile_id=data.profile_id,
            text_length=len(data.text),
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/synthesize/batch")
@limiter.limit("3/minute")
async def batch_synthesis(
    request: Request, data: BatchSynthesisRequest, db: DbSession, user: CurrentUser
) -> list[dict]:
    """Batch synthesize multiple lines."""
    logger.info(
        "batch_synthesis_called",
        line_count=len(data.lines),
        profile_id=data.profile_id,
        output_format=data.output_format,
    )
    try:
        results = await batch_synthesize(
            db,
            lines=data.lines,
            profile_id=data.profile_id,
            preset_id=data.preset_id,
            speed=data.speed,
            output_format=data.output_format,
        )
        logger.info(
            "batch_synthesis_succeeded",
            profile_id=data.profile_id,
            result_count=len(results),
        )
        return results
    except ValueError as e:
        logger.error(
            "batch_synthesis_failed",
            profile_id=data.profile_id,
            line_count=len(data.lines),
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/synthesis/history")
async def synthesis_history(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    profile_id: str | None = None,
) -> list[dict]:
    """Get synthesis history."""
    logger.info("synthesis_history_called", limit=limit, offset=offset, profile_id=profile_id)
    history = await get_history(db, limit=limit, offset=offset, profile_id=profile_id)
    logger.info("synthesis_history_returned", count=len(history), profile_id=profile_id)
    return [
        {
            "id": h.id,
            "profile_id": h.profile_id,
            "provider_name": h.provider_name,
            "text": h.text,
            "audio_url": f"/api/v1/audio/{Path(h.output_path).name}" if h.output_path else None,
            "output_format": h.output_format,
            "duration_seconds": h.duration_seconds,
            "latency_ms": h.latency_ms,
            "quality_wer": h.quality_wer,
            "quality_flagged": _is_quality_flagged(h.quality_wer),
            "created_at": h.created_at.isoformat(),
        }
        for h in history
    ]


# ---------------------------------------------------------------------------
# Feedback (SL-25)
# ---------------------------------------------------------------------------

# WER above this threshold flags a synthesis as potentially low-quality.
# Mirrors the default in ``app.tasks.preferences`` — kept in one place so the
# API response and the Celery side stay consistent.
QUALITY_WER_FLAG_THRESHOLD = 0.3


def _is_quality_flagged(quality_wer: float | None) -> bool:
    """Return True when a synthesis row's WER exceeds the quality threshold."""
    return quality_wer is not None and quality_wer > QUALITY_WER_FLAG_THRESHOLD


@router.post(
    "/synthesis/{history_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_synthesis_feedback(
    history_id: str,
    payload: FeedbackCreate,
    db: DbSession,
    user: CurrentUser,
) -> FeedbackResponse:
    """Record a thumbs up/down rating for a past synthesis.

    Returns 404 if the history row does not exist, 422 on invalid payload.
    """
    logger.info(
        "submit_synthesis_feedback_called",
        history_id=history_id,
        rating=payload.rating,
    )
    user_id = user.get("sub") if user else None
    try:
        row = await create_feedback(
            db,
            history_id=history_id,
            rating=payload.rating,
            tags=payload.tags,
            note=payload.note,
            user_id=user_id,
        )
    except NotFoundError as exc:
        logger.info("submit_synthesis_feedback_not_found", history_id=history_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail
        )
    return FeedbackResponse(**feedback_to_response_dict(row))


@router.get(
    "/synthesis/{history_id}/feedback",
    response_model=list[FeedbackResponse],
)
async def list_synthesis_feedback(
    history_id: str,
    db: DbSession,
    user: CurrentUser,
) -> list[FeedbackResponse]:
    """List all feedback entries for a specific synthesis history row."""
    rows = await list_feedback_for_history(db, history_id)
    return [FeedbackResponse(**feedback_to_response_dict(r)) for r in rows]
