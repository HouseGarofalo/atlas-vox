"""MCP tool definitions and handlers for Atlas Vox."""

from __future__ import annotations

import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TOOLS = [
    {
        "name": "atlas_vox_synthesize",
        "description": "Synthesize text to speech using a voice profile",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to synthesize"},
                "profile_id": {"type": "string", "description": "Voice profile ID"},
                "speed": {"type": "number", "description": "Speech speed (0.5–2.0)", "default": 1.0},
            },
            "required": ["text", "profile_id"],
        },
    },
    {
        "name": "atlas_vox_list_voices",
        "description": "List all available voice profiles",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "atlas_vox_train_voice",
        "description": "Start training a voice model from uploaded samples",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile_id": {"type": "string", "description": "Voice profile ID"},
                "provider_name": {"type": "string", "description": "Override provider (optional)"},
            },
            "required": ["profile_id"],
        },
    },
    {
        "name": "atlas_vox_get_training_status",
        "description": "Get the status of a training job",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Training job ID"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "atlas_vox_manage_profile",
        "description": "Create or update a voice profile",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "update", "delete"]},
                "profile_id": {"type": "string", "description": "Profile ID (for update/delete)"},
                "name": {"type": "string", "description": "Profile name (for create)"},
                "provider_name": {"type": "string", "description": "Provider (for create)"},
            },
            "required": ["action"],
        },
    },
    {
        "name": "atlas_vox_compare_voices",
        "description": "Compare the same text across multiple voice profiles",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to compare"},
                "profile_ids": {"type": "array", "items": {"type": "string"}, "description": "Profile IDs to compare"},
            },
            "required": ["text", "profile_ids"],
        },
    },
    {
        "name": "atlas_vox_provider_status",
        "description": "Get status and health of TTS providers",
        "inputSchema": {
            "type": "object",
            "properties": {
                "provider_name": {"type": "string", "description": "Specific provider (optional, omit for all)"},
            },
        },
    },
    {
        "name": "atlas_vox_speak",
        "description": "Speak text using any available voice. No profile needed. Just provide the text and optionally a voice name.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to speak"},
                "voice": {
                    "type": "string",
                    "description": "Voice name or ID (e.g., 'af_heart', 'en-US-JennyNeural', 'Rachel'). Defaults to Kokoro Heart.",
                },
                "provider": {
                    "type": "string",
                    "description": "Provider name (e.g., 'kokoro', 'azure_speech', 'elevenlabs'). Auto-detected from voice if omitted.",
                },
                "speed": {"type": "number", "description": "Speech speed (0.5-2.0)", "default": 1.0},
            },
            "required": ["text"],
        },
    },
    {
        "name": "atlas_vox_list_available_voices",
        "description": "List all available voices from all TTS providers (not profiles — actual provider voices).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string",
                    "description": "Filter to a specific provider (optional, omit for all providers).",
                },
            },
        },
    },
]


async def handle_tool_call(name: str, arguments: dict[str, Any]) -> dict:
    """Dispatch a tool call to the appropriate handler."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}

    try:
        result = await handler(arguments)
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}
    except Exception as e:
        logger.error("mcp_tool_error", tool=name, error=str(e))
        return {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}


async def _synthesize(args: dict) -> dict:
    from app.core.database import async_session_factory
    from app.services.synthesis_service import synthesize

    async with async_session_factory() as db:
        result = await synthesize(db, text=args["text"], profile_id=args["profile_id"], speed=args.get("speed", 1.0))
        await db.commit()
        return result


async def _list_voices(args: dict) -> list:
    from app.core.database import async_session_factory
    from app.services.profile_service import list_profiles

    async with async_session_factory() as db:
        profiles = await list_profiles(db)
        return [{"id": p.id, "name": p.name, "provider": p.provider_name, "status": p.status} for p in profiles]


async def _train_voice(args: dict) -> dict:
    from app.core.database import async_session_factory
    from app.services.training_service import start_training

    async with async_session_factory() as db:
        job = await start_training(db, args["profile_id"], provider_name=args.get("provider_name"))
        await db.commit()
        return {"job_id": job.id, "status": job.status, "provider": job.provider_name}


async def _get_training_status(args: dict) -> dict:
    from app.core.database import async_session_factory
    from app.services.training_service import get_job_status

    async with async_session_factory() as db:
        return await get_job_status(db, args["job_id"])


async def _manage_profile(args: dict) -> dict:
    from app.core.database import async_session_factory
    from app.schemas.profile import ProfileCreate, ProfileUpdate
    from app.services.profile_service import create_profile, delete_profile, update_profile

    action = args["action"]
    async with async_session_factory() as db:
        if action == "create":
            data = ProfileCreate(name=args["name"], provider_name=args.get("provider_name", "kokoro"))
            profile = await create_profile(db, data)
            await db.commit()
            return {"id": profile.id, "name": profile.name, "action": "created"}
        elif action == "update":
            data = ProfileUpdate(**{k: v for k, v in args.items() if k not in ("action", "profile_id")})
            profile = await update_profile(db, args["profile_id"], data)
            await db.commit()
            return {"id": profile.id, "action": "updated"} if profile else {"error": "Not found"}
        elif action == "delete":
            ok = await delete_profile(db, args["profile_id"])
            await db.commit()
            return {"deleted": ok}
        return {"error": f"Unknown action: {action}"}


async def _compare_voices(args: dict) -> dict:
    from app.core.database import async_session_factory
    from app.services.comparison_service import compare_voices

    async with async_session_factory() as db:
        results = await compare_voices(db, text=args["text"], profile_ids=args["profile_ids"])
        await db.commit()
        return {"text": args["text"], "results": results}


def _detect_provider(voice: str) -> str:
    """Auto-detect provider from voice ID patterns."""
    import re

    # Kokoro voices: af_*, am_*, bf_*, bm_* (language prefix + gender prefix + name)
    if re.match(r"^[a-z]{1,2}[fm]_", voice):
        return "kokoro"

    # Azure Neural voices: en-US-JennyNeural, en-GB-RyanNeural, etc.
    if re.match(r"^[a-z]{2}-[A-Z]{2}-\w+Neural$", voice):
        return "azure_speech"

    # Piper voices: en_US-*, en_GB-*, etc.
    if re.match(r"^[a-z]{2}_[A-Z]{2}-", voice):
        return "piper"

    # Known ElevenLabs voice IDs (24-char hex-ish IDs)
    known_elevenlabs = {
        "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "AZnzlk1XvdvUeBnXmlld",  # Domi
        "EXAVITQu4vr4xnSDxMaL",  # Bella
        "ErXwobaYiN019PkySvjV",  # Antoni
        "MF3mGyEYCl7XYWbV9V6O",  # Elli
        "TxGEqnHWrfWFTfGW9XjX",  # Josh
        "VR6AewLTigWG4xSOukaG",  # Arnold
        "pNInz6obpgDQGcFmaJgB",  # Adam
        "yoZ06aMxZJJ28mfd3POQ",  # Sam
    }
    if voice in known_elevenlabs:
        return "elevenlabs"

    # Coqui XTTS: names with spaces (e.g. "Claribel Dervla")
    if " " in voice:
        return "coqui_xtts"

    # Default to kokoro
    return "kokoro"


async def _speak(args: dict) -> dict:
    """Quick text-to-speech without profiles."""
    from app.providers.base import SynthesisSettings
    from app.services.provider_registry import provider_registry

    text = args["text"]
    voice = args.get("voice", "af_heart")
    provider_name = args.get("provider")
    speed = args.get("speed", 1.0)

    # Auto-detect provider from voice if not specified
    if not provider_name:
        provider_name = _detect_provider(voice)

    try:
        provider = provider_registry.get_provider(provider_name)
    except ValueError as e:
        return {"error": str(e), "available_providers": provider_registry.list_available()}

    settings = SynthesisSettings(speed=speed)
    result = await provider.synthesize(text, voice, settings)

    return {
        "audio_url": f"/api/v1/audio/{result.audio_path.name}",
        "provider": provider_name,
        "voice": voice,
        "format": result.format,
        "duration_seconds": result.duration_seconds,
    }


async def _list_available_voices(args: dict) -> dict:
    """List voices from all providers (or a specific one)."""
    from app.services.provider_registry import PROVIDER_DISPLAY_NAMES, provider_registry

    filter_provider = args.get("provider")
    voices: list[dict] = []
    providers_to_query = (
        [filter_provider] if filter_provider else provider_registry.list_available()
    )

    for name in providers_to_query:
        display_name = PROVIDER_DISPLAY_NAMES.get(name, name)
        try:
            provider = provider_registry.get_provider(name)
            provider_voices = await provider.list_voices()
            for v in provider_voices:
                voices.append({
                    "voice_id": v.voice_id,
                    "name": v.name,
                    "language": v.language,
                    "gender": v.gender,
                    "provider": name,
                    "provider_display": display_name,
                })
        except Exception as exc:
            logger.warning("voice_list_failed", provider=name, error=str(exc))
            continue

    return {"voices": voices, "count": len(voices)}


async def _provider_status(args: dict) -> Any:
    from app.services.provider_registry import provider_registry

    name = args.get("provider_name")
    if name:
        health = await provider_registry.health_check(name)
        caps = await provider_registry.get_capabilities(name)
        return {"name": name, "healthy": health.healthy, "latency_ms": health.latency_ms, "gpu_mode": caps.gpu_mode}
    else:
        results = []
        for p in provider_registry.list_all_known():
            if p["implemented"]:
                h = await provider_registry.health_check(p["name"])
                results.append({"name": p["name"], "display_name": p["display_name"], "healthy": h.healthy})
            else:
                results.append({"name": p["name"], "display_name": p["display_name"], "healthy": None})
        return results


_HANDLERS = {
    "atlas_vox_synthesize": _synthesize,
    "atlas_vox_list_voices": _list_voices,
    "atlas_vox_train_voice": _train_voice,
    "atlas_vox_get_training_status": _get_training_status,
    "atlas_vox_manage_profile": _manage_profile,
    "atlas_vox_compare_voices": _compare_voices,
    "atlas_vox_provider_status": _provider_status,
    "atlas_vox_speak": _speak,
    "atlas_vox_list_available_voices": _list_available_voices,
}
