"""SSE transport for the MCP server."""

from __future__ import annotations

import asyncio
import json

import structlog
from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.security import verify_api_key
from app.mcp.server import mcp_server

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])


async def _verify_mcp_auth(authorization: str | None = Header(None)) -> None:
    """Verify API key for MCP connections (skipped if auth disabled)."""
    if settings.auth_disabled:
        return
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MCP requires API key")
    # Extract key from "Bearer <key>" format
    key = authorization[7:] if authorization.startswith("Bearer ") else authorization
    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    # Validate against stored API keys
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.api_key import ApiKey

    async with async_session_factory() as db:
        result = await db.execute(select(ApiKey).where(ApiKey.active == True))  # noqa: E712
        keys = result.scalars().all()
        for stored_key in keys:
            if verify_api_key(key, stored_key.key_hash):
                return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@router.get("/sse")
async def mcp_sse_endpoint(request: Request) -> StreamingResponse:
    """SSE endpoint for MCP clients. Maintains a persistent connection."""
    await _verify_mcp_auth(request.headers.get("authorization"))

    async def event_stream():
        # Send initial connection event
        yield "event: endpoint\ndata: /mcp/message\n\n"

        # Keep connection alive
        try:
            while True:
                if await request.is_disconnected():
                    break
                yield "event: ping\ndata: {}\n\n"
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/message")
async def mcp_message_endpoint(request: Request) -> dict:
    """Handle JSONRPC 2.0 messages from MCP clients."""
    await _verify_mcp_auth(request.headers.get("authorization"))

    body = await request.body()
    response = await mcp_server.handle_message(body.decode())

    if response is None:
        return {}
    return json.loads(response)
