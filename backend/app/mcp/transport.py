"""SSE transport for the MCP server."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import verify_api_key
from app.mcp.server import mcp_server

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])

# Scopes granted to connections when auth is bypassed (AUTH_DISABLED=true).
_AUTH_DISABLED_SCOPES: list[str] = ["admin"]


async def _verify_mcp_auth(authorization: str | None) -> dict[str, Any]:
    """Verify API key for MCP connections (skipped if auth disabled).

    Returns a context dict containing at minimum a ``scopes`` list that
    tool handlers can use for fine-grained access control.
    """
    if settings.auth_disabled:
        logger.debug("mcp_auth_bypass", reason="AUTH_DISABLED")
        return {"sub": "local-user", "scopes": _AUTH_DISABLED_SCOPES}

    if not authorization:
        logger.warning("mcp_auth_failed", reason="missing_authorization_header")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MCP requires API key")

    # Extract key from "Bearer <key>" format
    key = authorization[7:] if authorization.startswith("Bearer ") else authorization
    if not key:
        logger.warning("mcp_auth_failed", reason="empty_api_key")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    # Validate against stored API keys. The key prefix (first 12 chars) is
    # indexed and carries ~72 bits of entropy — practically collision-free.
    # We take AT MOST one candidate and run Argon2 verify exactly once, so
    # auth latency is bounded and attackers cannot induce multi-hash CPU
    # burn by registering keys that share a hot prefix.
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.api_key import ApiKey

    prefix = key[:12] if len(key) >= 12 else key

    async with async_session_factory() as db:
        # .limit(1) is the whole timing mitigation — exactly one Argon2
        # verification regardless of collisions. If someone does manage to
        # register two keys with the same prefix, the second registration
        # will succeed at the ORM layer but only the first will ever be
        # reachable via MCP auth; that's acceptable and surface-able to
        # admins via /api/v1/admin/api-keys.
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.key_prefix == prefix,
                ApiKey.active.is_(True),
            ).limit(1)
        )
        stored_key = result.scalar_one_or_none()
        if stored_key is not None and verify_api_key(key, stored_key.key_hash):
            # Scopes are stored as a comma-separated string on the model,
            # or may be absent on older rows — default to read-only.
            raw_scopes: str = getattr(stored_key, "scopes", "") or ""
            scopes = [s.strip() for s in raw_scopes.split(",") if s.strip()] or ["read"]
            logger.debug("mcp_auth_success", scopes=scopes)
            return {"sub": stored_key.id, "scopes": scopes}

    logger.warning("mcp_auth_failed", reason="invalid_api_key")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@router.get("/sse")
async def mcp_sse_endpoint(request: Request) -> StreamingResponse:
    """SSE endpoint for MCP clients. Maintains a persistent connection."""
    auth_ctx = await _verify_mcp_auth(request.headers.get("authorization"))
    # Store auth context in request state so downstream tool calls can access it.
    request.state.mcp_auth = auth_ctx
    # Also set the ContextVar so tool handlers can read it via _mcp_auth_ctx_var.
    from app.mcp.tools import _mcp_auth_ctx_var
    _mcp_auth_ctx_var.set(auth_ctx)

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
@limiter.limit("60/minute")
async def mcp_message_endpoint(request: Request) -> dict:
    """Handle JSONRPC 2.0 messages from MCP clients."""
    auth_ctx = await _verify_mcp_auth(request.headers.get("authorization"))
    # Store auth context in request state so tool handlers can read it.
    request.state.mcp_auth = auth_ctx

    body = await request.body()
    # Bind the auth context into the current async context so tool handlers
    # can read it via get_mcp_auth_context() without requiring server.py changes.
    from app.mcp.tools import _mcp_auth_ctx_var
    token = _mcp_auth_ctx_var.set(auth_ctx)
    try:
        response = await mcp_server.handle_message(body.decode())
    finally:
        _mcp_auth_ctx_var.reset(token)

    if response is None:
        return {}
    return json.loads(response)
