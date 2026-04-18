"""IN-48: Agent SDK bridge tests.

Two layers:
  1. Schema validation — every tool must have the shape Anthropic's Tool
     API expects (name / description / input_schema with 'type' and
     'properties'). Required fields listed in input_schema must actually
     exist under properties.
  2. Dispatcher smoke tests using httpx.MockTransport to simulate the
     atlas-vox backend without spinning up FastAPI.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.agent_bridge import TOOL_SCHEMAS, ToolDispatcher, list_tool_names
from app.agent_bridge.tools import get_tool_schema


# ---------------------------------------------------------------------------
# Schema conformance
# ---------------------------------------------------------------------------


class TestToolSchemas:
    def test_schemas_are_non_empty(self):
        assert len(TOOL_SCHEMAS) >= 10

    def test_tool_names_match_registered_handlers(self):
        from app.agent_bridge.client import _HANDLERS

        schema_names = set(list_tool_names())
        handler_names = set(_HANDLERS.keys())
        assert schema_names == handler_names, (
            "schemas and handlers out of sync — every tool must be both "
            "declared in tools.py and dispatched in client.py"
        )

    @pytest.mark.parametrize("schema", TOOL_SCHEMAS, ids=[t["name"] for t in TOOL_SCHEMAS])
    def test_schema_has_required_keys(self, schema):
        assert "name" in schema and isinstance(schema["name"], str)
        assert schema["name"].startswith("atlas_vox_"), (
            "tool names should be namespaced so downstream agents can "
            "distinguish them from other SDK tools"
        )
        assert "description" in schema
        assert len(schema["description"]) > 20, "meaningful descriptions matter"
        assert "input_schema" in schema
        assert schema["input_schema"]["type"] == "object"
        assert "properties" in schema["input_schema"]

    @pytest.mark.parametrize("schema", TOOL_SCHEMAS, ids=[t["name"] for t in TOOL_SCHEMAS])
    def test_required_fields_exist_in_properties(self, schema):
        required = schema["input_schema"].get("required", [])
        props = schema["input_schema"]["properties"]
        for field in required:
            assert field in props, (
                f"{schema['name']} marks {field} required but does not declare it in properties"
            )

    def test_schemas_are_json_serializable(self):
        """Anthropic SDK serializes schemas over the wire — they must be JSON-safe."""
        json.dumps(TOOL_SCHEMAS)

    def test_get_tool_schema_lookup(self):
        assert get_tool_schema("atlas_vox_synthesize")["name"] == "atlas_vox_synthesize"
        assert get_tool_schema("does_not_exist") is None


# ---------------------------------------------------------------------------
# Dispatcher routing
# ---------------------------------------------------------------------------


def _transport(handler):
    """Build an httpx MockTransport from a single handler callable."""
    return httpx.MockTransport(handler)


class TestDispatcherDispatching:
    def test_synthesize_maps_to_post_synthesize(self):
        seen: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            seen["method"] = req.method
            seen["path"] = req.url.path
            seen["json"] = json.loads(req.content.decode())
            return httpx.Response(200, json={"audio_url": "/api/v1/audio/out.wav"})

        mock_client = httpx.Client(transport=_transport(handler))
        dispatcher = ToolDispatcher(base_url="http://x", client=mock_client)
        out = dispatcher.run(
            "atlas_vox_synthesize",
            {"text": "hi", "profile_id": "p1", "speed": 1.2},
        )
        assert out["audio_url"] == "/api/v1/audio/out.wav"
        assert seen["method"] == "POST"
        assert seen["path"] == "/api/v1/synthesize"
        assert seen["json"]["text"] == "hi"
        assert seen["json"]["speed"] == 1.2
        assert seen["json"]["output_format"] == "wav"

    def test_recommend_voice_maps_to_post_recommend(self):
        calls: list[httpx.Request] = []

        def handler(req: httpx.Request) -> httpx.Response:
            calls.append(req)
            return httpx.Response(
                200,
                json={"top_context": "narrative", "recommendations": []},
            )

        mock_client = httpx.Client(transport=_transport(handler))
        dispatcher = ToolDispatcher(base_url="http://x", client=mock_client)
        out = dispatcher.run(
            "atlas_vox_recommend_voice",
            {"text": "Long once-upon-a-time passage", "limit": 5},
        )
        assert out["top_context"] == "narrative"
        assert calls[0].method == "POST"
        assert calls[0].url.path == "/api/v1/synthesis/recommend-voice"
        assert json.loads(calls[0].content.decode())["limit"] == 5

    def test_list_profiles_maps_to_get(self):
        def handler(req: httpx.Request) -> httpx.Response:
            assert req.method == "GET"
            assert req.url.path == "/api/v1/profiles"
            return httpx.Response(200, json={"profiles": [], "count": 0})

        dispatcher = ToolDispatcher(
            base_url="http://x", client=httpx.Client(transport=_transport(handler)),
        )
        out = dispatcher.run("atlas_vox_list_profiles", {})
        assert out == {"profiles": [], "count": 0}

    def test_training_status_threads_job_id(self):
        def handler(req: httpx.Request) -> httpx.Response:
            assert req.url.path == "/api/v1/training/jobs/job-abc"
            return httpx.Response(200, json={"id": "job-abc", "status": "training"})

        dispatcher = ToolDispatcher(
            base_url="http://x", client=httpx.Client(transport=_transport(handler)),
        )
        out = dispatcher.run("atlas_vox_training_status", {"job_id": "job-abc"})
        assert out["status"] == "training"

    def test_quality_dashboard_passes_wer_limit(self):
        def handler(req: httpx.Request) -> httpx.Response:
            assert "wer_limit=25" in str(req.url)
            return httpx.Response(200, json={"profile_id": "p1", "overall_score": 88})

        dispatcher = ToolDispatcher(
            base_url="http://x", client=httpx.Client(transport=_transport(handler)),
        )
        dispatcher.run(
            "atlas_vox_quality_dashboard", {"profile_id": "p1", "wer_limit": 25},
        )

    def test_recommended_samples_passes_count(self):
        def handler(req: httpx.Request) -> httpx.Response:
            assert "count=7" in str(req.url)
            return httpx.Response(200, json={"recommendations": []})

        dispatcher = ToolDispatcher(
            base_url="http://x", client=httpx.Client(transport=_transport(handler)),
        )
        dispatcher.run(
            "atlas_vox_recommended_samples", {"profile_id": "p1", "count": 7},
        )


# ---------------------------------------------------------------------------
# Error surfacing
# ---------------------------------------------------------------------------


class TestDispatcherErrors:
    def test_unknown_tool_returns_error_dict(self):
        dispatcher = ToolDispatcher(
            base_url="http://x", client=httpx.Client(transport=_transport(lambda r: httpx.Response(200))),
        )
        out = dispatcher.run("atlas_vox_does_not_exist", {})
        assert "error" in out
        assert "Unknown tool" in out["error"]

    def test_backend_404_surfaces_as_error_dict(self):
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"detail": "Profile not found"})

        dispatcher = ToolDispatcher(
            base_url="http://x", client=httpx.Client(transport=_transport(handler)),
        )
        out = dispatcher.run(
            "atlas_vox_quality_dashboard", {"profile_id": "missing"},
        )
        assert out["error"] == "Profile not found"
        assert out["status_code"] == 404

    def test_auth_header_injected_when_api_key_set(self):
        seen: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            seen["auth"] = req.headers.get("authorization")
            return httpx.Response(200, json={"profiles": [], "count": 0})

        dispatcher = ToolDispatcher(
            base_url="http://x",
            api_key="avx_secretkey",
            client=httpx.Client(transport=_transport(handler)),
        )
        dispatcher.run("atlas_vox_list_profiles", {})
        assert seen["auth"] == "Bearer avx_secretkey"

    def test_context_manager_closes_client(self):
        """ToolDispatcher supports `with` for proper pool cleanup."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"profiles": [], "count": 0})

        with ToolDispatcher(
            base_url="http://x",
            client=httpx.Client(transport=_transport(handler)),
        ) as d:
            d.run("atlas_vox_list_profiles", {})
        # No explicit assertion — we're checking that __exit__ doesn't raise.
