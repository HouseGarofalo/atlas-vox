"""Synthesis service — text chunking, streaming, batch, presets, history."""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.persona_preset import PersonaPreset
from app.models.synthesis_history import SynthesisHistory
from app.models.voice_profile import VoiceProfile
from app.providers.base import AudioResult, SynthesisSettings
from app.services.provider_registry import provider_registry
from app.services.ssml_sanitizer import sanitize_ssml

logger = structlog.get_logger(__name__)

# Provider-specific character limits for text chunking
PROVIDER_CHAR_LIMITS: dict[str, int] = {
    "elevenlabs": 5000,
    "azure_speech": 3000,  # Conservative; Azure handles ~10 min of audio
    "kokoro": 2000,
    "coqui_xtts": 1500,
    "piper": 2000,
    "styletts2": 1000,
    "cosyvoice": 1500,
    "dia": 1000,
    "dia2": 1000,
}
CHUNK_MAX_CHARS_DEFAULT = 1500

# In-memory pronunciation cache: keyed by profile_id, stores (entries, timestamp).
# Global entries (profile_id=None) are cached under the key "__global__".
_pronunciation_cache: dict[str, tuple[list, float]] = {}
_PRONUNCIATION_CACHE_TTL = 60.0  # seconds
_PRONUNCIATION_CACHE_MAX_SIZE = 100

# Compiled regex cache for pronunciation patterns
_regex_cache: dict[str, re.Pattern] = {}

# Lock for thread-safe pronunciation cache access
_cache_lock = asyncio.Lock()


def _split_text(text: str, max_chars: int = CHUNK_MAX_CHARS_DEFAULT) -> list[str]:
    """Split long text at paragraph/sentence boundaries.

    Respects a configurable max_chars limit. First tries to split on paragraph
    breaks (double newline), then falls back to sentence boundaries, then word
    boundaries for very long sentences.
    """
    if len(text) <= max_chars:
        return [text]

    logger.debug("text_chunked", text_length=len(text), max_chars=max_chars)

    chunks: list[str] = []
    current = ""

    # First split on paragraph breaks, then sentence boundaries within each
    paragraphs = re.split(r"\n\s*\n", text)
    sentences: list[str] = []
    for para in paragraphs:
        para_sentences = re.split(r"(?<=[.!?])\s+", para.strip())
        sentences.extend(para_sentences)

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip() if current else sentence
        else:
            if current:
                chunks.append(current)
            # Handle very long sentences by splitting on words
            if len(sentence) > max_chars:
                words = sentence.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= max_chars:
                        current = f"{current} {word}".strip() if current else word
                    else:
                        if current:
                            chunks.append(current)
                        current = word
            else:
                current = sentence

    if current:
        chunks.append(current)
    return chunks


async def _apply_pronunciation(db: AsyncSession, text: str, profile_id: str) -> str:
    """Replace words matching pronunciation dictionary entries with SSML phoneme tags.

    Looks up global entries (profile_id IS NULL) and profile-specific entries.
    Uses an in-memory cache with TTL to avoid repeated DB queries during batch synthesis.
    Only applies if there are matching entries — returns original text otherwise.
    """
    from sqlalchemy import or_

    from app.models.pronunciation_entry import PronunciationEntry

    now = time.monotonic()
    entries: list = []

    # Check cache for global entries
    cache_key_global = "__global__"
    cache_key_profile = profile_id

    async with _cache_lock:
        cached_global = _pronunciation_cache.get(cache_key_global)
        cached_profile = _pronunciation_cache.get(cache_key_profile)

        if (
            cached_global is not None
            and (now - cached_global[1]) < _PRONUNCIATION_CACHE_TTL
            and cached_profile is not None
            and (now - cached_profile[1]) < _PRONUNCIATION_CACHE_TTL
        ):
            entries = cached_global[0] + cached_profile[0]
        else:
            result = await db.execute(
                select(PronunciationEntry).where(
                    or_(
                        PronunciationEntry.profile_id.is_(None),
                        PronunciationEntry.profile_id == profile_id,
                    )
                )
            )
            all_entries = result.scalars().all()

            global_entries = [e for e in all_entries if e.profile_id is None]
            profile_entries = [e for e in all_entries if e.profile_id == profile_id]

            _pronunciation_cache[cache_key_global] = (global_entries, now)
            _pronunciation_cache[cache_key_profile] = (profile_entries, now)

            # Evict oldest entries if cache exceeds max size
            if len(_pronunciation_cache) > _PRONUNCIATION_CACHE_MAX_SIZE:
                oldest_keys = sorted(
                    _pronunciation_cache,
                    key=lambda k: _pronunciation_cache[k][1],
                )[:_PRONUNCIATION_CACHE_MAX_SIZE // 2]
                for k in oldest_keys:
                    del _pronunciation_cache[k]

            entries = global_entries + profile_entries

    if not entries:
        return text

    # Apply replacements (case-insensitive word boundary matching)
    for entry in entries:
        # Use cached compiled regex for performance
        cache_key = entry.word.lower()
        pattern = _regex_cache.get(cache_key)
        if pattern is None:
            pattern = re.compile(rf"\b{re.escape(entry.word)}\b", re.IGNORECASE)
            _regex_cache[cache_key] = pattern

        replacement = f'<phoneme alphabet="ipa" ph="{entry.ipa}">{entry.word}</phoneme>'
        text = pattern.sub(replacement, text)

    return text


async def _resolve_profile(db: AsyncSession, profile_id: str) -> VoiceProfile:
    result = await db.execute(
        select(VoiceProfile).where(VoiceProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Profile")
    return profile


async def _resolve_voice_id(
    db: AsyncSession, profile: VoiceProfile, version_id: str | None = None,
) -> str:
    """Determine the voice_id to use for synthesis.

    Priority:
      0. explicit version_id  — for non-destructive version comparison
      1. profile.voice_id  — pre-built voice from provider library
      2. active version's provider_model_id  — trained/cloned voice
      3. "default"  — provider fallback
    """
    # If a specific version_id is requested (e.g., version comparison),
    # use it directly without changing the profile's active version.
    if version_id:
        from app.models.model_version import ModelVersion
        ver_result = await db.execute(
            select(ModelVersion).where(ModelVersion.id == version_id)
        )
        version = ver_result.scalar_one_or_none()
        if version and version.provider_model_id:
            voice_id = version.provider_model_id
            source = "explicit_version"
        else:
            voice_id = "default"
            source = "default"
    elif profile.voice_id:
        voice_id = profile.voice_id
        source = "profile_voice_id"
    elif profile.active_version_id:
        from app.models.model_version import ModelVersion
        ver_result = await db.execute(
            select(ModelVersion).where(ModelVersion.id == profile.active_version_id)
        )
        version = ver_result.scalar_one_or_none()
        if version and version.provider_model_id:
            voice_id = version.provider_model_id
            source = "active_version"
        else:
            voice_id = "default"
            source = "default"
    else:
        voice_id = "default"
        source = "default"
    logger.debug("voice_id_resolved", profile_id=profile.id, voice_id=voice_id, source=source)
    return voice_id


async def _apply_preset(db: AsyncSession, preset_id: str, synth_settings: SynthesisSettings) -> SynthesisSettings:
    """Apply preset values to synthesis settings."""
    result = await db.execute(
        select(PersonaPreset).where(PersonaPreset.id == preset_id)
    )
    preset = result.scalar_one_or_none()
    if preset is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Preset", preset_id)

    synth_settings.speed = preset.speed
    synth_settings.pitch = preset.pitch
    synth_settings.volume = preset.volume
    return synth_settings


async def _fire_synthesis_webhook_background(
    synthesis_id: str,
    profile_id: str,
    provider_name: str,
    latency_ms: int,
    duration_seconds: float | None = None,
) -> None:
    """Background webhook dispatch with its own DB session.

    Uses an independent session so the request-scoped session is not leaked
    into a background task that outlives the request.
    """
    from app.core.database import async_session_factory
    from app.services.webhook_dispatcher import fire_synthesis_complete

    try:
        async with async_session_factory() as session:
            await fire_synthesis_complete(
                session,
                synthesis_id=synthesis_id,
                profile_id=profile_id,
                provider_name=provider_name,
                latency_ms=latency_ms,
                duration_seconds=duration_seconds,
            )
    except Exception as exc:
        logger.warning("webhook_synthesis_background_failed", error=str(exc))


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
    """Synthesize text using a voice profile's provider.

    Handles text chunking for long input and concatenates results.
    Applies pronunciation dictionary entries as SSML phoneme tags.
    """
    # Sanitize SSML before sending to any provider
    if ssml:
        text = sanitize_ssml(text)

    # Apply text preprocessing (number/date/abbreviation expansion) before TTS
    if preprocess and not ssml:
        from app.services.text_preprocessor import preprocess_text
        text = preprocess_text(text)

    # Apply pronunciation dictionary (global + profile-specific entries)
    if not ssml:
        text = await _apply_pronunciation(db, text, profile_id)

    profile = await _resolve_profile(db, profile_id)

    logger.info(
        "synthesis_started",
        profile_id=profile_id,
        text_length=len(text),
        provider=profile.provider_name,
        preset_id=preset_id,
        output_format=output_format,
        ssml=ssml,
    )

    synth_settings = SynthesisSettings(
        speed=speed, pitch=pitch, volume=volume,
        output_format=output_format, ssml=ssml,
        voice_settings=voice_settings,
    )
    if preset_id:
        synth_settings = await _apply_preset(db, preset_id, synth_settings)

    provider = provider_registry.get_provider(profile.provider_name)

    # voice_settings are passed per-request to synthesize() — NOT applied to
    # the shared provider singleton to avoid race conditions under concurrent use.
    # The provider's synthesize() method applies them locally.

    voice_id = await _resolve_voice_id(db, profile, version_id=version_id)

    start = time.perf_counter()

    # Split long text into chunks
    # Use provider-specific chunk limit for optimal quality
    chunk_limit = PROVIDER_CHAR_LIMITS.get(profile.provider_name, CHUNK_MAX_CHARS_DEFAULT)
    chunks = _split_text(text, max_chars=chunk_limit)

    word_boundaries = None

    try:
        # Word boundary synthesis (single-chunk only)
        if include_word_boundaries and len(chunks) == 1:
            capabilities = await provider.get_capabilities()
            if capabilities.supports_word_boundaries:
                result, word_boundaries = await provider.synthesize_with_word_boundaries(
                    chunks[0], voice_id, synth_settings
                )
            else:
                result = await provider.synthesize(chunks[0], voice_id, synth_settings)
        elif len(chunks) == 1:
            result = await provider.synthesize(chunks[0], voice_id, synth_settings)
        else:
            # Synthesize chunks and concatenate
            import numpy as np
            import soundfile as sf

            all_audio = []
            sample_rate = 22050
            for chunk in chunks:
                chunk_result = await provider.synthesize(chunk, voice_id, synth_settings)
                audio, sr = sf.read(str(chunk_result.audio_path))
                all_audio.append(audio)
                sample_rate = sr

            combined = np.concatenate(all_audio)
            output_dir = Path(settings.storage_path) / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            combined_file = output_dir / f"synth_{uuid.uuid4().hex[:12]}.wav"
            sf.write(str(combined_file), combined, sample_rate)

            result = AudioResult(
                audio_path=combined_file,
                duration_seconds=len(combined) / sample_rate,
                sample_rate=sample_rate,
                format="wav",
            )
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            "synthesis_failed",
            profile_id=profile_id,
            provider=profile.provider_name,
            text_length=len(text),
            latency_ms=latency_ms,
            error=str(exc),
        )
        raise

    latency_ms = int((time.perf_counter() - start) * 1000)

    # Format conversion if needed
    if output_format != "wav" and result.format == "wav":
        result = await _convert_format(result, output_format)

    logger.info(
        "synthesis_completed",
        profile_id=profile_id,
        provider=profile.provider_name,
        latency_ms=latency_ms,
        duration_seconds=result.duration_seconds,
        output_format=result.format,
        chunk_count=len(chunks),
    )

    # Save to history
    history = SynthesisHistory(
        profile_id=profile_id,
        provider_name=profile.provider_name,
        text=text[:1000],  # Truncate for storage
        output_path=str(result.audio_path),
        output_format=result.format,
        duration_seconds=result.duration_seconds,
        latency_ms=latency_ms,
        settings_json=json.dumps({
            "speed": synth_settings.speed,
            "pitch": synth_settings.pitch,
            "volume": synth_settings.volume,
            "preset_id": preset_id,
        }),
    )
    db.add(history)

    # Track usage for analytics (E2)
    from app.models.usage_event import UsageEvent
    usage = UsageEvent(
        provider_name=profile.provider_name,
        profile_id=profile_id,
        voice_id=voice_id,
        characters=len(text),
        duration_ms=latency_ms,
        event_type="synthesis",
    )
    db.add(usage)
    await db.flush()

    # Embed deepfake watermark (SC-45). Skipped when disabled in settings.
    # Best-effort: any failure logs a warning but does not break synthesis.
    # Watermarks are embedded in the WAV carrier; for non-WAV outputs
    # embed_watermark returns the sibling .wav file, and we rewrite the
    # history record + response to point at it so downloads receive the
    # watermarked file.
    if not settings.disable_watermark:
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

    # Dispatch synthesis.complete webhook (best-effort, non-blocking)
    try:
        import asyncio

        asyncio.create_task(_fire_synthesis_webhook_background(
            synthesis_id=history.id,
            profile_id=profile_id,
            provider_name=profile.provider_name,
            latency_ms=latency_ms,
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

    # Build audio URL
    filename = Path(result.audio_path).name
    audio_url = f"/api/v1/audio/{filename}"

    resp = {
        "id": history.id,
        "audio_url": audio_url,
        "duration_seconds": result.duration_seconds,
        "latency_ms": latency_ms,
        "profile_id": profile_id,
        "provider_name": profile.provider_name,
    }
    if word_boundaries:
        resp["word_boundaries"] = [
            {"text": wb.text, "offset_ms": wb.offset_ms,
             "duration_ms": wb.duration_ms, "word_index": wb.word_index}
            for wb in word_boundaries
        ]
    return resp


async def stream_synthesize(
    db: AsyncSession,
    text: str,
    profile_id: str,
    speed: float = 1.0,
    pitch: float = 0.0,
    output_format: str = "wav",
) -> AsyncIterator[bytes]:
    """Stream synthesis — yields audio chunks as they're generated."""
    profile = await _resolve_profile(db, profile_id)
    provider = provider_registry.get_provider(profile.provider_name)

    logger.info(
        "stream_synthesis_started",
        profile_id=profile_id,
        text_length=len(text),
        provider=profile.provider_name,
        output_format=output_format,
    )

    capabilities = await provider.get_capabilities()
    if not capabilities.supports_streaming:
        from app.core.exceptions import ProviderError
        raise ProviderError(profile.provider_name, "does not support streaming")

    voice_id = await _resolve_voice_id(db, profile)
    synth_settings = SynthesisSettings(speed=speed, pitch=pitch, output_format=output_format)
    chunk_index = 0
    async for chunk in provider.stream_synthesize(text, voice_id, synth_settings):
        logger.debug("stream_chunk_sent", profile_id=profile_id, chunk_index=chunk_index, chunk_bytes=len(chunk))
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
    """Batch synthesize multiple lines concurrently with controlled parallelism.

    Uses asyncio.gather with a semaphore to process lines in parallel while
    limiting concurrent provider calls to avoid overwhelming resources.
    Each concurrent task gets its own DB session to avoid async session conflicts.

    Args:
        _session_factory: Optional override for the session factory (used in testing).
            If None, uses the default async_session_factory.
    """
    import asyncio

    from app.core.database import async_session_factory

    session_factory = _session_factory or async_session_factory

    MAX_CONCURRENT = 4  # Limit parallel provider calls

    stripped = [line.strip() for line in lines if line.strip()]
    if not stripped:
        return []

    logger.info(
        "batch_synthesis_started",
        profile_id=profile_id,
        line_count=len(stripped),
        preset_id=preset_id,
        output_format=output_format,
    )

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    caller_owns_session = _session_factory is not None

    async def _synth_one(line: str) -> dict:
        async with semaphore:
            async with session_factory() as session:
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

    # When caller provides a session factory, the tasks share one session and
    # must run sequentially to avoid concurrent flush errors.
    if caller_owns_session:
        results = [await _synth_one(line) for line in stripped]
    else:
        results = await asyncio.gather(*[_synth_one(line) for line in stripped])
    logger.info(
        "batch_synthesis_completed",
        profile_id=profile_id,
        result_count=len(results),
    )
    return list(results)


async def get_history(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
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


async def _convert_format(result: AudioResult, target_format: str) -> AudioResult:
    """Convert audio to target format using pydub."""
    logger.info(
        "format_conversion",
        source_format=result.format,
        target_format=target_format,
        source_path=str(result.audio_path),
    )
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _convert_format_sync, result, target_format)
    except ImportError:
        logger.warning("pydub_not_installed", hint="pip install pydub")
        return result  # Fall back to original format
    except Exception as e:
        logger.error("format_conversion_failed", source_format=result.format, target_format=target_format, error=str(e))
        raise


def _convert_format_sync(result: AudioResult, target_format: str) -> AudioResult:
    """Synchronous format conversion using pydub."""
    from pydub import AudioSegment

    audio = AudioSegment.from_file(str(result.audio_path))
    output_path = result.audio_path.with_suffix(f".{target_format}")
    audio.export(str(output_path), format=target_format)

    return AudioResult(
        audio_path=output_path,
        duration_seconds=result.duration_seconds,
        sample_rate=result.sample_rate,
        format=target_format,
    )
