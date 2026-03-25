"""Synthesis endpoints — single, stream, batch, history."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.synthesis import (
    BatchSynthesisRequest,
    SynthesisRequest,
    SynthesisResponse,
)
from app.services.synthesis_service import (
    batch_synthesize,
    get_history,
    stream_synthesize,
    synthesize,
)

router = APIRouter(tags=["synthesis"])


@router.post("/synthesize", response_model=SynthesisResponse)
async def synthesize_text(
    data: SynthesisRequest, db: DbSession, user: CurrentUser
) -> SynthesisResponse:
    """Synthesize text to speech, return audio URL."""
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
        )
        return SynthesisResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/synthesize/stream")
async def stream_synthesis(
    data: SynthesisRequest, db: DbSession, user: CurrentUser
) -> StreamingResponse:
    """Stream synthesis — chunked transfer encoding for streaming providers."""
    try:
        audio_stream = stream_synthesize(
            db,
            text=data.text,
            profile_id=data.profile_id,
            speed=data.speed,
            pitch=data.pitch,
        )
        return StreamingResponse(
            audio_stream,
            media_type="audio/wav",
            headers={"Transfer-Encoding": "chunked"},
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/synthesize/batch")
async def batch_synthesis(
    data: BatchSynthesisRequest, db: DbSession, user: CurrentUser
) -> list[dict]:
    """Batch synthesize multiple lines."""
    try:
        return await batch_synthesize(
            db,
            lines=data.lines,
            profile_id=data.profile_id,
            preset_id=data.preset_id,
            speed=data.speed,
            output_format=data.output_format,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/synthesis/history")
async def synthesis_history(
    db: DbSession,
    user: CurrentUser,
    limit: int = 50,
    profile_id: str | None = None,
) -> list[dict]:
    """Get synthesis history."""
    history = await get_history(db, limit=limit, profile_id=profile_id)
    return [
        {
            "id": h.id,
            "profile_id": h.profile_id,
            "provider_name": h.provider_name,
            "text": h.text,
            "audio_url": f"/api/v1/audio/{h.output_path.split('/')[-1]}" if h.output_path else None,
            "output_format": h.output_format,
            "duration_seconds": h.duration_seconds,
            "latency_ms": h.latency_ms,
            "created_at": h.created_at.isoformat(),
        }
        for h in history
    ]
