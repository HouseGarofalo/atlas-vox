"""FastAPI endpoints for the self-healing subsystem."""

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.healing.engine import healing_engine
from app.healing.models import Incident

logger = structlog.get_logger("atlas_vox.healing.api")

router = APIRouter(prefix="/healing", tags=["healing"])


@router.get("/status")
async def get_healing_status():
    """Get current self-healing engine status."""
    return healing_engine.get_status()


@router.get("/incidents")
async def list_incidents(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    severity: str | None = Query(None),
    category: str | None = Query(None),
):
    """List recent self-healing incidents."""
    query = select(Incident).order_by(desc(Incident.created_at)).limit(limit)
    if severity:
        query = query.where(Incident.severity == severity)
    if category:
        query = query.where(Incident.category == category)
    result = await db.execute(query)
    incidents = result.scalars().all()
    return {
        "incidents": [
            {
                "id": i.id,
                "severity": i.severity,
                "category": i.category,
                "title": i.title,
                "description": i.description,
                "detection_rule": i.detection_rule,
                "action_taken": i.action_taken,
                "action_detail": i.action_detail,
                "outcome": i.outcome,
                "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in incidents
        ],
        "count": len(incidents),
    }


@router.post("/check")
async def force_health_check():
    """Force an immediate health check."""
    snap = await healing_engine.health.check_now()
    return {
        "healthy": snap.healthy,
        "checks": snap.checks,
        "consecutive_failures": healing_engine.health.consecutive_failures,
    }


@router.post("/toggle")
async def toggle_healing(enable: bool = Query(...)):
    """Enable or disable the self-healing engine."""
    if enable and not healing_engine._running:
        await healing_engine.start()
    elif not enable and healing_engine._running:
        await healing_engine.stop()
    healing_engine.enabled = enable
    logger.info("healing_toggled", enabled=enable)
    return {"enabled": healing_engine.enabled, "running": healing_engine._running}


@router.get("/mcp/status")
async def get_mcp_status():
    """Get Claude Code MCP bridge status."""
    return healing_engine.mcp_bridge.status


@router.post("/mcp/review")
async def request_review(context: str = Query(..., min_length=10)):
    """Request a read-only code review from Claude Code."""
    result = await healing_engine.mcp_bridge.review_code(context)
    return {"context": context, "review": result}
