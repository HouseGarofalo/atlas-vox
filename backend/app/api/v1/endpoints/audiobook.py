"""Audiobook rendering endpoints.

POST /audiobook/render
    Synchronously render a markdown manuscript into a single MP3 using the
    given voice profile.  Returns the output path, duration, and chapter
    markers suitable for embedding in the player UI.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import CurrentUser, DbSession
from app.services.audiobook_stitcher import (
    AudiobookResult,
    render_audiobook,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/audiobook", tags=["audiobook"])


class AudiobookRenderRequest(BaseModel):
    profile_id: str = Field(..., description="Voice profile used for narration")
    markdown: str = Field(..., min_length=1, max_length=1_000_000)
    project_id: str | None = None
    crossfade_ms: int = Field(default=300, ge=0, le=5000)
    target_lufs: float = Field(default=-16.0, ge=-40.0, le=-6.0)
    preset_id: str | None = None
    output_format: str = Field(default="mp3")


class ChapterMarkerOut(BaseModel):
    index: int
    title: str
    start_seconds: float
    end_seconds: float


class AudiobookRenderResponse(BaseModel):
    output_path: str
    output_filename: str
    audio_url: str
    duration_seconds: float
    paragraph_count: int
    chapter_markers: list[ChapterMarkerOut]
    loudness_lufs: float | None = None
    loudness_fallback: bool = False


def _serialize(result: AudiobookResult) -> AudiobookRenderResponse:
    filename = result.output_path.name
    return AudiobookRenderResponse(
        output_path=str(result.output_path),
        output_filename=filename,
        audio_url=f"/api/v1/audio/{filename}",
        duration_seconds=result.duration_seconds,
        paragraph_count=result.paragraph_count,
        chapter_markers=[
            ChapterMarkerOut(
                index=m.index,
                title=m.title,
                start_seconds=m.start_seconds,
                end_seconds=m.end_seconds,
            )
            for m in result.chapter_markers
        ],
        loudness_lufs=result.loudness_lufs,
        loudness_fallback=result.loudness_fallback,
    )


@router.post("/render", response_model=AudiobookRenderResponse)
async def render_endpoint(
    body: AudiobookRenderRequest,
    db: DbSession,
    user: CurrentUser,
) -> AudiobookRenderResponse:
    """Render a long-form audiobook from markdown."""
    try:
        result = await render_audiobook(
            db,
            project_id=body.project_id,
            markdown=body.markdown,
            profile_id=body.profile_id,
            options={
                "crossfade_ms": body.crossfade_ms,
                "target_lufs": body.target_lufs,
                "preset_id": body.preset_id,
                "output_format": body.output_format,
            },
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.error("audiobook_render_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audiobook render failed: {exc}",
        ) from exc

    return _serialize(result)
