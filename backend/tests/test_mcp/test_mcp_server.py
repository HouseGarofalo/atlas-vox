"""Tests for MCP server JSONRPC handling."""

from __future__ import annotations

import json

import pytest

from app.mcp.server import MCPServer


@pytest.fixture
def mcp():
    return MCPServer()


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
    assert len(tools) == 7
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
