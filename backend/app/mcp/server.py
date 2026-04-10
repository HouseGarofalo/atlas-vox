"""Atlas Vox MCP Server — JSONRPC 2.0 handler with tool/resource registration."""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.mcp.tools import TOOLS, handle_tool_call

logger = structlog.get_logger(__name__)

RESOURCES = {
    "atlas-vox://profiles": {
        "uri": "atlas-vox://profiles",
        "name": "Voice Profiles",
        "description": "List of all voice profiles in Atlas Vox",
        "mimeType": "application/json",
    },
    "atlas-vox://providers": {
        "uri": "atlas-vox://providers",
        "name": "TTS Providers",
        "description": "Available TTS providers and their status",
        "mimeType": "application/json",
    },
}


class MCPServer:
    """JSONRPC 2.0 MCP server."""

    def __init__(self) -> None:
        self.initialized = False

    async def handle_message(self, raw: str) -> str | None:
        """Process a JSONRPC 2.0 message and return the response."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return self._error_response(None, -32700, "Parse error")

        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params", {})

        # Notifications (no id) don't get responses
        if msg_id is None and method not in ("initialize",):
            return None

        handler = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "ping": self._handle_ping,
        }.get(method)

        if handler is None:
            return self._error_response(msg_id, -32601, f"Method not found: {method}")

        try:
            result = await handler(params)
            return self._success_response(msg_id, result)
        except Exception as e:
            logger.error("mcp_handler_error", method=method, error=str(e))
            return self._error_response(msg_id, -32603, str(e))

    async def _handle_initialize(self, params: dict) -> dict:
        from app.core.config import settings
        self.initialized = True
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
            },
            "serverInfo": {
                "name": "atlas-vox",
                "version": settings.app_version,
            },
        }

    async def _handle_ping(self, params: dict) -> dict:
        return {}

    async def _handle_tools_list(self, params: dict) -> dict:
        return {"tools": TOOLS}

    async def _handle_tools_call(self, params: dict) -> dict:
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        return await handle_tool_call(name, arguments)

    async def _handle_resources_list(self, params: dict) -> dict:
        return {"resources": list(RESOURCES.values())}

    async def _handle_resources_read(self, params: dict) -> dict:
        uri = params.get("uri", "")
        if uri not in RESOURCES:
            raise ValueError(f"Unknown resource: {uri}")

        content = await self._read_resource(uri)
        return {
            "contents": [{
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(content),
            }],
        }

    async def _read_resource(self, uri: str) -> Any:
        from app.core.database import async_session_factory

        if uri == "atlas-vox://profiles":
            from app.services.profile_service import list_profiles
            async with async_session_factory() as db:
                profiles = await list_profiles(db)
                return [{"id": p.id, "name": p.name, "provider": p.provider_name, "status": p.status} for p in profiles]

        elif uri == "atlas-vox://providers":
            from app.services.provider_registry import provider_registry
            return provider_registry.list_all_known()

        return {}

    def _success_response(self, msg_id: Any, result: Any) -> str:
        return json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result})

    def _error_response(self, msg_id: Any, code: int, message: str) -> str:
        return json.dumps({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})


# Singleton
mcp_server = MCPServer()
