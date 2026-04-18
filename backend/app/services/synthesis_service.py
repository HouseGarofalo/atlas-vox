"""Synthesis orchestrator — coordinates pronunciation, chunking, providers, history.

Heavy lifting (pronunciation lookups, text chunking, cost math, audio
concatenation) lives in sibling services. This module is the thin glue that:

* Resolves the profile + voice in one eager DB round-trip (P2-22)
* Applies preprocessing / SSML / pronunciation / preset overrides
* Calls the provider through the registry
* Writes a :class:`SynthesisHistory` row stamped with cost + latency
* Fires the ``synthesis.complete`` webhook in the background

Public surface: :func:`synthesize`, :func:`batch_synthesize`,
:func:`stream_synthesize`, :func:`get_history`.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings as _app_settings
from app.models.persona_preset import PersonaPreset
from app.models.synthesis_history import SynthesisHistory
from app.models.voice_profile import VoiceProfile
from app.providers.base import SynthesisSettings
from app.services.audio_concat import convert_format, synthesize_and_concat
from app.services.cost_estimator import estimate_cost_usd
from app.services.provider_registry import provider_registry
from app.services.pronunciation_service import (
    _pronunciation_cache,  # re-exported for legacy importers (tests / endpoints)
    apply_pronunciation as _apply_pronunciation,
)
from app.services.ssml_sanitizer import sanitize_ssml
from app.services.text_chunking import (
    CHUNK_MAX_CHARS_DEFAULT,
    PROVIDER_CHAR_LIMITS,
    chunk_limit_for,
    split_text as _split_text,
)

logger = structlog.get_logger(__name__)

# Re-exports kept so existing imports (and the test suite) keep working.
__all__ = [
    "CHUNK_MAX_CHARS_DEFAULT",
    "PROVIDER_CHAR_LIMITS",
    "_apply_pronunciation",
    "_pronunciation_cache",
    "_split_text",
    "batch_synthesize",
    "get_history",
    "stream_synthesize",
    "synthesize",
]


async def _resolve_profile(db: AsyncSession, profile_id: str) -> VoiceProfile:
    """Load a profile plus its model versions in a single round-trip.

    P2-22 — previously the synthesize path loaded the profile, then separately
    queried the active ``ModelVersion`` for voice ID resolution. We now
    eagerly load ``versions`` via ``selectinload`` so voice resolution adds
    zero round-trips over the base profile load.
    """
    result = await db.execute(
        select(VoiceProfile)
        .where(VoiceProfile.id == profile_id)
        .options(selectinload(VoiceProfile.versions))
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Profile")
    return profile


def _resolve_voice_id_from_profile(
    profile: VoiceProfile, version_id: str | None = None,
) -> str:
    """Pick the ``voice_id`` handed to the provider.

    Priority:
      0. explicit ``version_id`` — non-destructive version comparison
      1. ``profile.voice_id`` — pre-built voice from the provider library
      2. active version's ``provider_model_id`` — trained / cloned voice
      3. ``"default"`` — provider fallback

    Reads exclusively from the already-eager-loaded ``profile.versions``.
    """
    if version_id:
        matched = next((v for v in profile.versions if v.id == version_id), None)
        voice_id = matched.provider_model_id if matched and matched.provider_model_id else "default"
        source = "explicit_version" if voice_id != "default" else "default"
    elif profile.voice_id:
        voice_id, source = profile.voice_id, "profile_voice_id"
    elif profile.active_version_id:
        matched = next(
            (v for v in profile.versions if v.id == profile.active_version_id), None,
        )
        voice_id = matched.provider_model_id if matched and matched.provider_model_id else "default"
        source = "active_version" if voice_id != "default" else "default"
    else:
        voice_id, source = "default", "default"
    logger.debug(
        "voice_id_resolved", profile_id=profile.id, voice_id=voice_id, source=source,
    )
    return voice_id


async def _apply_preset(
    db: AsyncSession, preset_id: str, synth_settings: SynthesisSettings,
) -> SynthesisSettings:
    """Apply preset values to synthesis settings."""
    result = await db.execute(select(PersonaPreset).where(PersonaPreset.id == preset_id))
    preset = result.scalar_one_or_none()
    if preset is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Preset", preset_id)
    synth_settings.speed = preset.speed
    synth_settings.pitch = preset.pitch
    synth_settings.volume = preset.volume
    return synth_settings


async def _fire_synthesis_webhook_background(
    synthesis_id: str, profile_id: str, provider_name: str,
    latency_ms: int, duration_seconds: float | None = None,
) -> None:
    """Fire ``synthesis.complete`` on an independent DB session."""
    from app.core.database import async_session_factory
    from app.services.webhook_dispatcher import fire_synthesis_complete

    try:
        async with async_session_factory() as session:
            await fire_synthesis_complete(
                session,
                synthesis_id=synthesis_id, profile_id=profile_id,
                provider_name=provider_name, latency_ms=latency_ms,
                duration_seconds=duration_seconds,
            )
    except Exception as exc:
        logger.warning("webhook_synthesis_background_failed", error=str(exc))


async def _run_provider(
    provider, chunks: list[str], voice_id: str, synth_settings: SynthesisSettings,
    include_word_boundaries: bool,
):
    """Dispatch to the provider — single chunk, multi-chunk concat, or word-boundary path."""
    if include_word_boundaries and len(chunks) == 1:
        capabilities = await provider.get_capabilities()
        if capabilities.supports_word_boundaries:
            return await provider.synthesize_with_word_boundaries(
                chunks[0], voice_id, synth_settings,
            )
        return await provider.synthesize(chunks[0], voice_id, synth_settings), None
    if len(chunks) == 1:
        return await provider.synthesize(chunks[0], voice_id, synth_settings), None
    return await synthesize_and_concat(provider, chunks, voice_id, synth_settings), None


async def synthesize(
    db: AsyncSession,
    text: str,
    profile_id: str,
    preset_id: str | None = None,
    speed: float = 1.0,
    pitch: float = 0.0,
    volume: float = 1.0,
    output_format: str = "wav",
    ssml: bool = False,
    include_word_boundaries: bool = False,
    voice_settings: dict | None = None,
    version_id: str | None = None,
    preprocess: bool = False,
) -> dict:
    """Synthesize ``text`` using ``profile_id`` and persist a history row."""
    if ssml:
        text = sanitize_ssml(text)
    if preprocess and not ssml:
        from app.services.text_preprocessor import preprocess_text
        text = preprocess_text(text)
    if not ssml:
        text = await _apply_pronunciation(db, text, profile_id)

    profile = await _resolve_profile(db, profile_id)

    logger.info(
        "synthesis_started",
        profile_id=profile_id, text_length=len(text),
        provider=profile.provider_name, preset_id=preset_id,
        output_format=output_format, ssml=ssml,
    )

    synth_settings = SynthesisSettings(
        speed=speed, pitch=pitch, volume=volume,
        output_format=output_format, ssml=ssml,
        voice_settings=voice_settings,
    )
    if preset_id:
        synth_settings = await _apply_preset(db, preset_id, synth_settings)

    provider = provider_registry.get_provider(profile.provider_name)
    voice_id = _resolve_voice_id_from_profile(profile, version_id=version_id)

    start = time.perf_counter()
    chunks = _split_text(text, max_chars=chunk_limit_for(profile.provider_name))

    try:
        result, word_boundaries = await _run_provider(
            provider, chunks, voice_id, synth_settings, include_word_boundaries,
        )
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            "synthesis_failed",
            profile_id=profile_id, provider=profile.provider_name,
            text_length=len(text), latency_ms=latency_ms, error=str(exc),
        )
        raise

    latency_ms = int((time.perf_counter() - start) * 1000)

    if output_format != "wav" and result.format == "wav":
        result = await convert_format(result, output_format)

    logger.info(
        "synthesis_completed",
        profile_id=profile_id, provider=profile.provider_name,
        latency_ms=latency_ms, duration_seconds=result.duration_seconds,
        output_format=result.format, chunk_count=len(chunks),
    )

    cost_usd = estimate_cost_usd(profile.provider_name, len(text))

    history = SynthesisHistory(
        profile_id=profile_id,
        provider_name=profile.provider_name,
        text=text[:1000],
        output_path=str(result.audio_path),
        output_format=result.format,
        duration_seconds=result.duration_seconds,
        latency_ms=latency_ms,
        estimated_cost_usd=cost_usd,
        settings_json=json.dumps({
            "speed": synth_settings.speed, "pitch": synth_settings.pitch,
            "volume": synth_settings.volume, "preset_id": preset_id,
        }),
    )
    db.add(history)

    from app.models.usage_event import UsageEvent
    db.add(UsageEvent(
        provider_name=profile.provider_name, profile_id=profile_id,
        voice_id=voice_id, characters=len(text), duration_ms=latency_ms,
        event_type="synthesis",
    ))
    await db.flush()

    # Embed deepfake watermark (SC-45). Best-effort — never break synthesis.
    if not _app_settings.disable_watermark:
        try:
            from app.services.audio_watermark import embed_watermark, make_payload

            payload = make_payload(profile_id, history.id)
            watermarked_path = embed_watermark(Path(result.audio_path), payload)
            if str(watermarked_path) != str(result.audio_path):
                history.output_path = str(watermarked_path)
                history.output_format = "wav"
                result.audio_path = watermarked_path
                result.format = "wav"
                await db.flush()
        except Exception as wm_exc:
            logger.warning(
                "watermark_embed_failed",
                profile_id=profile_id,
                history_id=history.id,
                error=str(wm_exc),
            )

    try:
        asyncio.create_task(_fire_synthesis_webhook_background(
            synthesis_id=history.id, profile_id=profile_id,
            provider_name=profile.provider_name, latency_ms=latency_ms,
            duration_seconds=result.duration_seconds,
        ))
    except Exception as wh_exc:
        logger.warning("webhook_synthesis_complete_failed", error=str(wh_exc))

    # SL-28 — fire-and-forget Whisper verification (WER vs. input text).
    # Broker unavailable (e.g. unit tests without Redis) must never fail
    # synthesis, so we swallow dispatch errors and only log them.
    try:
        from app.tasks.preferences import verify_synthesis
        verify_synthesis.delay(history.id)
    except Exception as vs_exc:
        logger.warning("verify_synthesis_dispatch_failed", error=str(vs_exc))

    resp = {
        "id": history.id,
        "audio_url": f"/api/v1/audio/{Path(result.audio_path).name}",
        "duration_seconds": result.duration_seconds,
        "latency_ms": latency_ms,
        "profile_id": profile_id,
        "provider_name": profile.provider_name,
        "estimated_cost_usd": cost_usd,
    }
    if word_boundaries:
        resp["word_boundaries"] = [
            {"text": wb.text, "offset_ms": wb.offset_ms,
             "duration_ms": wb.duration_ms, "word_index": wb.word_index}
            for wb in word_boundaries
        ]
    return resp


async def stream_synthesize(
    db: AsyncSession, text: str, profile_id: str,
    speed: float = 1.0, pitch: float = 0.0, output_format: str = "wav",
) -> AsyncIterator[bytes]:
    """Stream synthesis — yields audio chunks as they're generated."""
    profile = await _resolve_profile(db, profile_id)
    provider = provider_registry.get_provider(profile.provider_name)

    logger.info(
        "stream_synthesis_started",
        profile_id=profile_id, text_length=len(text),
        provider=profile.provider_name, output_format=output_format,
    )

    capabilities = await provider.get_capabilities()
    if not capabilities.supports_streaming:
        from app.core.exceptions import ProviderError
        raise ProviderError(profile.provider_name, "does not support streaming")

    voice_id = _resolve_voice_id_from_profile(profile)
    synth_settings = SynthesisSettings(speed=speed, pitch=pitch, output_format=output_format)
    chunk_index = 0
    async for chunk in provider.stream_synthesize(text, voice_id, synth_settings):
        logger.debug(
            "stream_chunk_sent",
            profile_id=profile_id, chunk_index=chunk_index, chunk_bytes=len(chunk),
        )
        chunk_index += 1
        yield chunk


async def batch_synthesize(
    db: AsyncSession,
    lines: list[str],
    profile_id: str,
    preset_id: str | None = None,
    speed: float = 1.0,
    output_format: str = "wav",
    _session_factory: Any | None = None,
) -> list[dict]:
    """Batch synthesize multiple lines concurrently with controlled parallelism."""
    from app.core.database import async_session_factory

    session_factory = _session_factory or async_session_factory
    MAX_CONCURRENT = 4

    stripped = [line.strip() for line in lines if line.strip()]
    if not stripped:
        return []

    logger.info(
        "batch_synthesis_started",
        profile_id=profile_id, line_count=len(stripped),
        preset_id=preset_id, output_format=output_format,
    )

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    caller_owns_session = _session_factory is not None

    async def _synth_one(line: str) -> dict:
        async with semaphore, session_factory() as session:
            try:
                result = await synthesize(
                    session, text=line, profile_id=profile_id,
                    preset_id=preset_id, speed=speed, output_format=output_format,
                )
                if caller_owns_session:
                    await session.flush()
                else:
                    await session.commit()
                return result
            except Exception:
                if not caller_owns_session:
                    await session.rollback()
                raise

    if caller_owns_session:
        results = [await _synth_one(line) for line in stripped]
    else:
        results = await asyncio.gather(*[_synth_one(line) for line in stripped])
    logger.info(
        "batch_synthesis_completed",
        profile_id=profile_id, result_count=len(results),
    )
    return list(results)


async def get_history(
    db: AsyncSession, limit: int = 50, offset: int = 0,
    profile_id: str | None = None,
) -> list[SynthesisHistory]:
    """Get synthesis history with pagination."""
    query = (
        select(SynthesisHistory)
        .order_by(SynthesisHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if profile_id:
        query = query.where(SynthesisHistory.profile_id == profile_id)
    result = await db.execute(query)
    return list(result.scalars().all())
