"""Synthesis endpoints — single, stream, batch, history."""

import time
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.synthesis import (
    BatchSynthesisRequest,
    SynthesisRequest,
    SynthesisResponse,
)
from app.core.rate_limit import limiter
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
@limiter.limit("10/minute")
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
            "created_at": h.created_at.isoformat(),
        }
        for h in history
    ]
