"""Agent SDK tool schemas for Atlas Vox.

Each tool is a standalone dict matching Anthropic's tool-use schema
(``name``, ``description``, ``input_schema``). The dispatcher maps the
tool name onto a concrete HTTP call in :mod:`app.agent_bridge.client`.

Adding a new tool:
  1. Append a schema dict to ``TOOL_SCHEMAS``.
  2. Register the handler in ``_HANDLERS`` in ``client.py``.
  3. Add a test in ``tests/test_services/test_agent_bridge.py``.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

_SYNTHESIZE_TOOL: dict[str, Any] = {
    "name": "atlas_vox_synthesize",
    "description": (
        "Synthesize text to speech using an Atlas Vox voice profile. "
        "Returns the output audio URL and metadata. Use this when the user "
        "asks to read aloud, narrate, voice, or speak a piece of text."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to synthesize. Supports SSML when ssml=true.",
                "minLength": 1,
                "maxLength": 10000,
            },
            "profile_id": {
                "type": "string",
                "description": "Atlas Vox voice profile ID (from list_profiles).",
            },
            "speed": {
                "type": "number",
                "description": "Playback speed multiplier (0.5-2.0). Default 1.0.",
                "minimum": 0.5,
                "maximum": 2.0,
            },
            "pitch": {
                "type": "number",
                "description": "Pitch adjustment in semitones (-50..+50). Default 0.",
                "minimum": -50,
                "maximum": 50,
            },
            "ssml": {
                "type": "boolean",
                "description": "Treat text as SSML markup.",
            },
            "output_format": {
                "type": "string",
                "enum": ["wav", "mp3", "ogg"],
                "description": "Output audio format. Default wav.",
            },
        },
        "required": ["text", "profile_id"],
    },
}


_RECOMMEND_VOICE_TOOL: dict[str, Any] = {
    "name": "atlas_vox_recommend_voice",
    "description": (
        "SL-30 context-adaptive routing. Classifies the given text "
        "(conversational / narrative / emotional / technical / dialogue / "
        "long_form) and returns the best matching Atlas Vox profiles. Use "
        "this BEFORE calling synthesize when the user hasn't specified "
        "a profile."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "minLength": 1,
                "maxLength": 20000,
            },
            "limit": {
                "type": "integer",
                "description": "Max number of recommendations (1-10). Default 3.",
                "minimum": 1,
                "maximum": 10,
            },
        },
        "required": ["text"],
    },
}


_LIST_PROFILES_TOOL: dict[str, Any] = {
    "name": "atlas_vox_list_profiles",
    "description": (
        "List all voice profiles in Atlas Vox with their status, "
        "provider, sample count, and version count. Use this to show "
        "the user what voices are available or find a profile ID."
    ),
    "input_schema": {"type": "object", "properties": {}},
}


_LIST_VOICES_TOOL: dict[str, Any] = {
    "name": "atlas_vox_list_voices",
    "description": (
        "List built-in (library) voices across all enabled providers. "
        "Useful when the user wants to explore ready-to-use voices "
        "without training their own profile."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Optional filter by provider name (e.g. 'kokoro').",
            },
            "language": {
                "type": "string",
                "description": "Optional filter by language code (e.g. 'en', 'ja').",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 500,
            },
        },
    },
}


_START_TRAINING_TOOL: dict[str, Any] = {
    "name": "atlas_vox_start_training",
    "description": (
        "Start a training / voice-cloning job for a profile. The job runs "
        "asynchronously; poll with get_training_status or list_training_jobs. "
        "Returns the job ID."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "profile_id": {"type": "string"},
            "provider_name": {
                "type": "string",
                "description": "Optional provider override (defaults to profile's provider).",
            },
        },
        "required": ["profile_id"],
    },
}


_TRAINING_STATUS_TOOL: dict[str, Any] = {
    "name": "atlas_vox_training_status",
    "description": (
        "Get the status of a training job — queued, running, completed, "
        "or failed — with progress percentage and any error message."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"job_id": {"type": "string"}},
        "required": ["job_id"],
    },
}


_QUALITY_DASHBOARD_TOOL: dict[str, Any] = {
    "name": "atlas_vox_quality_dashboard",
    "description": (
        "VQ-36 per-profile quality rollup. Returns WER time-series, "
        "per-version metrics, rating distribution, sample health, and "
        "an overall quality score. Use this to answer 'how good is "
        "this voice?' questions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "profile_id": {"type": "string"},
            "wer_limit": {
                "type": "integer",
                "description": "Max WER points to return (1-500). Default 50.",
                "minimum": 1,
                "maximum": 500,
            },
        },
        "required": ["profile_id"],
    },
}


_RECOMMENDED_SAMPLES_TOOL: dict[str, Any] = {
    "name": "atlas_vox_recommended_samples",
    "description": (
        "SL-29 active-learning. Given a profile, return the next N "
        "sentences the user should record to maximally fill phoneme "
        "gaps. Use when the user asks 'what should I record next?'"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "profile_id": {"type": "string"},
            "count": {
                "type": "integer",
                "minimum": 1,
                "maximum": 30,
            },
        },
        "required": ["profile_id"],
    },
}


_RENDER_AUDIOBOOK_TOOL: dict[str, Any] = {
    "name": "atlas_vox_render_audiobook",
    "description": (
        "AP-41 long-form rendering. Takes markdown, splits by chapter/"
        "paragraph, synthesizes each chunk, concatenates with crossfade, "
        "LUFS-normalizes, and returns the final audio URL + chapter "
        "markers. For audiobooks, podcasts, and narration projects."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "markdown": {
                "type": "string",
                "description": "Full markdown body. Headings become chapters.",
                "minLength": 1,
            },
            "profile_id": {"type": "string"},
        },
        "required": ["markdown", "profile_id"],
    },
}


_LIST_PROVIDERS_TOOL: dict[str, Any] = {
    "name": "atlas_vox_list_providers",
    "description": (
        "List all TTS providers with their capabilities (cloning, "
        "SSML, streaming, fine-tuning) and health status. Use this "
        "to pick a provider matching a specific need."
    ),
    "input_schema": {"type": "object", "properties": {}},
}


TOOL_SCHEMAS: list[dict[str, Any]] = [
    _SYNTHESIZE_TOOL,
    _RECOMMEND_VOICE_TOOL,
    _LIST_PROFILES_TOOL,
    _LIST_VOICES_TOOL,
    _START_TRAINING_TOOL,
    _TRAINING_STATUS_TOOL,
    _QUALITY_DASHBOARD_TOOL,
    _RECOMMENDED_SAMPLES_TOOL,
    _RENDER_AUDIOBOOK_TOOL,
    _LIST_PROVIDERS_TOOL,
]


def list_tool_names() -> list[str]:
    """Return the flat list of tool names for quick introspection."""
    return [t["name"] for t in TOOL_SCHEMAS]


def get_tool_schema(name: str) -> dict[str, Any] | None:
    """Fetch one schema by name — handy for tests and custom dispatchers."""
    for t in TOOL_SCHEMAS:
        if t["name"] == name:
            return t
    return None
