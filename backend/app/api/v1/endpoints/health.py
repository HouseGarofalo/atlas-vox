"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """System health check."""
    return {
        "status": "healthy",
        "service": "atlas-vox",
        "version": "0.1.0",
    }
