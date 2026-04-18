"""Audio file serving endpoint."""


from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.dependencies import CurrentUser
from app.core.rate_limit import limiter

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["audio"])

MIME_TYPES = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
    "opus": "audio/opus",
}

ALLOWED_AUDIO_EXTENSIONS = frozenset(MIME_TYPES.keys())


def _safe_audio_path(base_dir: Path, filename: str) -> Path:
    """Sanitize filename and resolve to a safe path within base_dir.

    Prevents path traversal, blocks non-audio extensions, and verifies
    the resolved path stays within the expected directory.
    """
    clean = Path(filename).name
    if not clean or ".." in clean or "/" in clean or "\\" in clean:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
    ext = clean.rsplit(".", 1)[-1].lower() if "." in clean else ""
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid audio file type")
    full = (base_dir / clean).resolve()
    if not str(full).startswith(str(base_dir.resolve())):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path traversal detected")
    return full


@router.get("/audio/previews/{filename}")
@limiter.limit("120/minute")
async def serve_preview_audio(request: Request, filename: str, user: CurrentUser) -> FileResponse:
    """Serve cached voice preview files."""
    base_dir = Path(settings.storage_path) / "output" / "previews"
    file_path = _safe_audio_path(base_dir, filename)
    logger.info("serve_preview_audio_called", filename=file_path.name)

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview audio file not found")

    ext = file_path.suffix.lstrip(".")
    media_type = MIME_TYPES.get(ext, "application/octet-stream")
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )


@router.get("/audio/{filename}")
@limiter.limit("120/minute")
async def serve_audio(request: Request, filename: str, user: CurrentUser) -> FileResponse:
    """Serve generated audio files from the output storage directory."""
    base_dir = Path(settings.storage_path) / "output"
    file_path = _safe_audio_path(base_dir, filename)
    logger.info("serve_audio_called", filename=file_path.name)

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")

    ext = file_path.suffix.lstrip(".")
    media_type = MIME_TYPES.get(ext, "application/octet-stream")
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )


@router.get("/audio/design/{filename}")
@limiter.limit("120/minute")
async def serve_audio_design(request: Request, filename: str, user: CurrentUser) -> FileResponse:
    """Serve audio files from the Audio Design Studio working directory."""
    base_dir = Path(settings.storage_path) / "audio-design"
    file_path = _safe_audio_path(base_dir, filename)

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio design file not found")

    ext = file_path.suffix.lstrip(".")
    media_type = MIME_TYPES.get(ext, "application/octet-stream")
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
    )


@router.get("/audio/{filename}/verify-watermark")
@limiter.limit("60/minute")
async def verify_audio_watermark(
    request: Request, filename: str, user: CurrentUser
) -> dict:
    """Attempt to recover the deepfake watermark embedded in an audio file.

    Returns the payload and confidence if found; 404 otherwise.
    """
    from app.services.audio_watermark import verify_watermark

    base_dir = Path(settings.storage_path) / "output"
    file_path = _safe_audio_path(base_dir, filename)

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found"
        )

    result = verify_watermark(file_path)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No watermark detected in this audio file",
        )
    logger.info(
        "verify_audio_watermark_ok",
        filename=file_path.name,
        confidence=result.get("confidence"),
    )
    return {
        "filename": file_path.name,
        "payload": result["payload"],
        "confidence": result["confidence"],
    }
