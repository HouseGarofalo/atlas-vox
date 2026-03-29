"""Comparison endpoint — side-by-side voice synthesis."""

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from app.core.dependencies import CurrentUser, DbSession
from app.core.rate_limit import limiter
from app.schemas.synthesis import CompareRequest, CompareResponse, CompareResult
from app.services.comparison_service import compare_voices

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["comparison"])


@router.post("/compare", response_model=CompareResponse)
@limiter.limit("5/minute")
async def compare_voices_endpoint(
    request: Request, data: CompareRequest, db: DbSession, user: CurrentUser
) -> CompareResponse:
    """Compare the same text across multiple voice profiles."""
    if len(data.profile_ids) > 10:
        logger.warning(
            "compare_limit_exceeded",
            requested=len(data.profile_ids),
            max_allowed=10,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare more than 10 profiles at once",
        )
    logger.info(
        "compare_voices_called",
        profile_count=len(data.profile_ids),
        text_length=len(data.text),
    )
    try:
        results = await compare_voices(
            db,
            text=data.text,
            profile_ids=data.profile_ids,
            speed=data.speed,
            pitch=data.pitch,
        )
        successful = [r for r in results if "error" not in r]
        logger.info(
            "compare_voices_succeeded",
            profile_count=len(data.profile_ids),
            successful_count=len(successful),
        )
        return CompareResponse(
            text=data.text,
            results=[CompareResult(**r) for r in successful],
        )
    except ValueError as e:
        logger.error(
            "compare_voices_failed",
            profile_count=len(data.profile_ids),
            text_length=len(data.text),
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
