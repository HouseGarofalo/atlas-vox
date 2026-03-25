"""Comparison endpoint — side-by-side voice synthesis."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.synthesis import CompareRequest, CompareResponse, CompareResult
from app.services.comparison_service import compare_voices

router = APIRouter(tags=["comparison"])


@router.post("/compare", response_model=CompareResponse)
async def compare_voices_endpoint(
    data: CompareRequest, db: DbSession, user: CurrentUser
) -> CompareResponse:
    """Compare the same text across multiple voice profiles."""
    try:
        results = await compare_voices(
            db,
            text=data.text,
            profile_ids=data.profile_ids,
            speed=data.speed,
            pitch=data.pitch,
        )
        return CompareResponse(
            text=data.text,
            results=[CompareResult(**r) for r in results if "error" not in r],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
