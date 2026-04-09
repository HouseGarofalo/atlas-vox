"""Authentication status endpoints."""

from __future__ import annotations

import structlog
from fastapi import APIRouter

from app.core.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["auth"])


@router.get("/auth/status")
async def auth_status() -> dict:
    """Return whether authentication is enabled or disabled.

    This endpoint is always public so the frontend can determine
    whether to show the login screen or auto-authenticate.
    """
    return {"auth_disabled": settings.auth_disabled}
