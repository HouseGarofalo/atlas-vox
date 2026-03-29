"""Tests for MCP server JSONRPC handling."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mcp.server import MCPServer


@pytest.fixture
def mcp():
    return MCPServer()


# ---------------------------------------------------------------------------
# Existing tests (preserved)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initialize(mcp: MCPServer):
    response = await mcp.handle_message(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}
    }))
    data = json.loads(response)
    assert data["result"]["serverInfo"]["name"] == "atlas-vox"
    assert mcp.initialized is True


@pytest.mark.asyncio
async def test_ping(mcp: MCPServer):
    response = await mcp.handle_message(json.dumps({
        "jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}
    }))
    data = json.loads(response)
    assert data["result"] == {}


@pytest.mark.asyncio
async def test_tools_list(mcp: MCPServer):
    response = await mcp.handle_message(json.dumps({
        "jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}
    }))
    data = json.loads(response)
    tools = data["result"]["tools"]
    assert len(tools) == 9  # 7 original + atlas_vox_speak + atlas_vox_list_available_voices
    names = {t["name"] for t in tools}
    assert "atlas_vox_synthesize" in names
    assert "atlas_vox_list_voices" in names


@pytest.mark.asyncio
async def test_resources_list(mcp: MCPServer):
    response = await mcp.handle_message(json.dumps({
        "jsonrpc": "2.0", "id": 4, "method": "resources/list", "params": {}
    }))
    data = json.loads(response)
    resources = data["result"]["resources"]
    assert len(resources) == 2
    uris = {r["uri"] for r in resources}
    assert "atlas-vox://profiles" in uris
    assert "atlas-vox://providers" in uris


@pytest.mark.asyncio
async def test_unknown_method(mcp: MCPServer):
    response = await mcp.handle_message(json.dumps({
        "jsonrpc": "2.0", "id": 5, "method": "unknown/method", "params": {}
    }))
    data = json.loads(response)
    assert "error" in data
    assert data["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_invalid_json(mcp: MCPServer):
    response = await mcp.handle_message("not json")
    data = json.loads(response)
    assert data["error"]["code"] == -32700


# ---------------------------------------------------------------------------
# tools/call
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tools_call_list_voices(mcp: MCPServer):
    """tools/call for atlas_vox_list_voices returns a valid content response."""
    from types import SimpleNamespace

    fake_profiles = [
        SimpleNamespace(id="p1", name="Voice One", provider_name="kokoro", status="ready"),
    ]

    # The handler imports async_session_factory and list_profiles locally at
    # call time, so we patch at their source modules.
    mock_db = AsyncMock()
    mock_db_cm = MagicMock()
    mock_db_cm.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("app.core.database.async_session_factory", return_value=mock_db_cm):
        with patch("app.services.profile_service.list_profiles", new=AsyncMock(return_value=fake_profiles)):
            response = await mcp.handle_message(json.dumps({
                "jsonrpc": "2.0", "id": 10, "method": "tools/call",
                "params": {"name": "atlas_vox_list_voices", "arguments": {}},
            }))

    data = json.loads(response)
    assert "result" in data
    assert "content" in data["result"]
    assert isinstance(data["result"]["content"], list)
    assert len(data["result"]["content"]) >= 1
    # Content is JSON text — parse and check structure
    payload = json.loads(data["result"]["content"][0]["text"])
    assert isinstance(payload, list)
    assert payload[0]["id"] == "p1"


@pytest.mark.asyncio
async def test_tools_call_unknown_tool(mcp: MCPServer):
    """Calling a tool that doesn't exist must return isError=True."""
    response = await mcp.handle_message(json.dumps({
        "jsonrpc": "2.0", "id": 11, "method": "tools/call",
        "params": {"name": "atlas_vox_does_not_exist", "arguments": {}},
    }))
    data = json.loads(response)
    # The handler returns a result (not a JSONRPC error) with isError=True
    assert "result" in data
    assert data["result"].get("isError") is True
    content_text = data["result"]["content"][0]["text"]
    assert "Unknown tool" in content_text


# ---------------------------------------------------------------------------
# resources/read
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resources_read_profiles(mcp: MCPServer):
    """Reading atlas-vox://profiles resource returns a contents list."""
    from types import SimpleNamespace

    fake_profiles = [
        SimpleNamespace(id="p1", name="My Voice", provider_name="kokoro", status="ready"),
    ]

    # _read_resource imports async_session_factory and list_profiles locally,
    # so patch at their canonical module paths.
    mock_db = AsyncMock()
    mock_db_cm = MagicMock()
    mock_db_cm.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("app.core.database.async_session_factory", return_value=mock_db_cm):
        with patch("app.services.profile_service.list_profiles", new=AsyncMock(return_value=fake_profiles)):
            response = await mcp.handle_message(json.dumps({
                "jsonrpc": "2.0", "id": 20, "method": "resources/read",
                "params": {"uri": "atlas-vox://profiles"},
            }))

    data = json.loads(response)
    assert "result" in data
    contents = data["result"]["contents"]
    assert len(contents) == 1
    assert contents[0]["uri"] == "atlas-vox://profiles"
    assert contents[0]["mimeType"] == "application/json"
    payload = json.loads(contents[0]["text"])
    assert isinstance(payload, list)
    assert payload[0]["id"] == "p1"


@pytest.mark.asyncio
async def test_resources_read_providers(mcp: MCPServer):
    """Reading atlas-vox://providers resource returns a contents list."""
    fake_provider_list = [
        {"name": "kokoro", "display_name": "Kokoro", "implemented": True},
    ]

    mock_registry = MagicMock()
    mock_registry.list_all_known.return_value = fake_provider_list

    # provider_registry is imported locally inside _read_resource
    with patch("app.services.provider_registry.provider_registry", mock_registry):
        response = await mcp.handle_message(json.dumps({
            "jsonrpc": "2.0", "id": 21, "method": "resources/read",
            "params": {"uri": "atlas-vox://providers"},
        }))

    data = json.loads(response)
    assert "result" in data
    contents = data["result"]["contents"]
    assert len(contents) == 1
    assert contents[0]["uri"] == "atlas-vox://providers"
    payload = json.loads(contents[0]["text"])
    assert isinstance(payload, list)
    assert payload[0]["name"] == "kokoro"


@pytest.mark.asyncio
async def test_resources_read_unknown(mcp: MCPServer):
    """Reading an unknown URI must return a JSONRPC error response."""
    response = await mcp.handle_message(json.dumps({
        "jsonrpc": "2.0", "id": 22, "method": "resources/read",
        "params": {"uri": "atlas-vox://does-not-exist"},
    }))
    data = json.loads(response)
    assert "error" in data
    assert data["error"]["code"] == -32603


# ---------------------------------------------------------------------------
# Scope enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tools_call_scope_denied():
    """Tool call with insufficient scopes returns an error result."""
    from app.mcp.tools import _mcp_auth_ctx_var

    # Set context to a user with only "read" scope — cannot synthesize
    token = _mcp_auth_ctx_var.set({"sub": "test-user", "scopes": ["read"]})
    try:
        server = MCPServer()
        response = await server.handle_message(json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "atlas_vox_synthesize",
                "arguments": {"text": "hello", "profile_id": "test"},
            },
            "id": 10,
        }))
        resp = json.loads(response)
        # The tool handler returns a result dict (not a JSONRPC error); the
        # dict content will contain "error" or "scope"/"denied" wording.
        result_str = json.dumps(resp)
        assert (
            resp.get("result", {}).get("isError") is True
            or "scope" in result_str.lower()
            or "denied" in result_str.lower()
            or "permission" in result_str.lower()
        )
    finally:
        _mcp_auth_ctx_var.reset(token)
