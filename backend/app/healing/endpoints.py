"""FastAPI endpoints for the self-healing subsystem."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.healing.engine import SelfHealingEngine

router = APIRouter(prefix="/healing", tags=["healing"])

# Module-level engine instance — started/stopped by the application lifespan
healing_engine = SelfHealingEngine()


@router.get("/status")
async def get_healing_status():
    """Get the current status of the self-healing system."""
    return healing_engine.get_status()


@router.post("/start")
async def start_healing():
    """Start the self-healing engine."""
    await healing_engine.start()
    return {"status": "started"}


@router.post("/stop")
async def stop_healing():
    """Stop the self-healing engine."""
    await healing_engine.stop()
    return {"status": "stopped"}


@router.get("/mcp/status")
async def get_mcp_status():
    """Get Claude Code MCP bridge status."""
    return healing_engine.mcp_bridge.status


@router.post("/mcp/review")
async def request_review(context: str = Query(..., min_length=10)):
    """Request a read-only code review from Claude Code."""
    result = await healing_engine.mcp_bridge.review_code(context)
    return {"context": context, "review": result}
