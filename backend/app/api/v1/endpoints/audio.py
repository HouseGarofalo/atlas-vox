"""Audio file serving endpoint."""


from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.dependencies import CurrentUser

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["audio"])

MIME_TYPES = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
}


@router.get("/audio/previews/{filename}")
async def serve_preview_audio(filename: str, user: CurrentUser) -> FileResponse:
    """Serve cached voice preview files."""
    safe_name = Path(filename).name
    file_path = Path(settings.storage_path) / "output" / "previews" / safe_name
    logger.info("serve_preview_audio_called", filename=safe_name)

    if not file_path.exists():
        logger.info("serve_preview_audio_not_found", filename=safe_name)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview audio file not found")

    ext = file_path.suffix.lstrip(".")
    media_type = MIME_TYPES.get(ext, "application/octet-stream")
    logger.info("serve_preview_audio_serving", filename=safe_name, media_type=media_type)

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=safe_name,
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )


@router.get("/audio/{filename}")
async def serve_audio(filename: str, user: CurrentUser) -> FileResponse:
    """Serve generated audio files from the output storage directory."""
    # Sanitize filename — prevent directory traversal
    safe_name = Path(filename).name
    file_path = Path(settings.storage_path) / "output" / safe_name
    logger.info("serve_audio_called", filename=safe_name)

    if not file_path.exists():
        logger.info("serve_audio_not_found", filename=safe_name)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")

    ext = file_path.suffix.lstrip(".")
    media_type = MIME_TYPES.get(ext, "application/octet-stream")
    logger.info("serve_audio_serving", filename=safe_name, media_type=media_type)

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=safe_name,
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )
