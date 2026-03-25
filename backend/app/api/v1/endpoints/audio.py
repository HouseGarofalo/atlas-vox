"""Audio file serving endpoint."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.dependencies import CurrentUser

router = APIRouter(tags=["audio"])

MIME_TYPES = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
}


@router.get("/audio/{filename}")
async def serve_audio(filename: str, user: CurrentUser) -> FileResponse:
    """Serve generated audio files from the output storage directory."""
    # Sanitize filename — prevent directory traversal
    safe_name = Path(filename).name
    file_path = Path(settings.storage_path) / "output" / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")

    ext = file_path.suffix.lstrip(".")
    media_type = MIME_TYPES.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=safe_name,
    )
