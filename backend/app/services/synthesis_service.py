"""Synthesis service — text chunking, streaming, batch, presets, history."""

from __future__ import annotations

import json
import re
import time
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.persona_preset import PersonaPreset
from app.models.synthesis_history import SynthesisHistory
from app.models.voice_profile import VoiceProfile
from app.providers.base import AudioResult, SynthesisSettings
from app.services.provider_registry import provider_registry

logger = structlog.get_logger(__name__)

# Max chars per chunk for long text splitting
CHUNK_MAX_CHARS = 1000


def _split_text(text: str, max_chars: int = CHUNK_MAX_CHARS) -> list[str]:
    """Split long text at sentence boundaries."""
    if len(text) <= max_chars:
        return [text]

    logger.debug("text_chunked", text_length=len(text), max_chars=max_chars)

    chunks: list[str] = []
    current = ""
    # Split on sentence-ending punctuation
    sentences = re.split(r"(?<=[.!?])\s+", text)

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip() if current else sentence
        else:
            if current:
                chunks.append(current)
            # Handle very long sentences
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


async def _resolve_profile(db: AsyncSession, profile_id: str) -> VoiceProfile:
    result = await db.execute(
        select(VoiceProfile).where(VoiceProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise ValueError("Profile not found")
    return profile


async def _resolve_voice_id(db: AsyncSession, profile: VoiceProfile) -> str:
    """Determine the voice_id to use for synthesis.

    Priority:
      1. profile.voice_id  — pre-built voice from provider library
      2. active version's provider_model_id  — trained/cloned voice
      3. "default"  — provider fallback
    """
    if profile.voice_id:
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
        raise ValueError(f"Preset '{preset_id}' not found")

    synth_settings.speed = preset.speed
    synth_settings.pitch = preset.pitch
    synth_settings.volume = preset.volume
    return synth_settings


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
) -> dict:
    """Synthesize text using a voice profile's provider.

    Handles text chunking for long input and concatenates results.
    """
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
    )
    if preset_id:
        synth_settings = await _apply_preset(db, preset_id, synth_settings)

    provider = provider_registry.get_provider(profile.provider_name)
    voice_id = await _resolve_voice_id(db, profile)

    start = time.perf_counter()

    # Split long text into chunks
    chunks = _split_text(text)

    try:
        if len(chunks) == 1:
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
    await db.flush()

    # Build audio URL
    filename = Path(result.audio_path).name
    audio_url = f"/api/v1/audio/{filename}"

    return {
        "id": history.id,
        "audio_url": audio_url,
        "duration_seconds": result.duration_seconds,
        "latency_ms": latency_ms,
        "profile_id": profile_id,
        "provider_name": profile.provider_name,
    }


async def stream_synthesize(
    db: AsyncSession,
    text: str,
    profile_id: str,
    speed: float = 1.0,
    pitch: float = 0.0,
) -> AsyncIterator[bytes]:
    """Stream synthesis — yields audio chunks as they're generated."""
    profile = await _resolve_profile(db, profile_id)
    provider = provider_registry.get_provider(profile.provider_name)

    logger.info(
        "stream_synthesis_started",
        profile_id=profile_id,
        text_length=len(text),
        provider=profile.provider_name,
    )

    capabilities = await provider.get_capabilities()
    if not capabilities.supports_streaming:
        raise ValueError(f"Provider '{profile.provider_name}' does not support streaming")

    voice_id = await _resolve_voice_id(db, profile)
    synth_settings = SynthesisSettings(speed=speed, pitch=pitch)
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
) -> list[dict]:
    """Batch synthesize multiple lines, returning results for each."""
    logger.info(
        "batch_synthesis_started",
        profile_id=profile_id,
        line_count=len(lines),
        preset_id=preset_id,
        output_format=output_format,
    )
    results = []
    for line in lines:
        if not line.strip():
            continue
        result = await synthesize(
            db, text=line.strip(), profile_id=profile_id,
            preset_id=preset_id, speed=speed, output_format=output_format,
        )
        results.append(result)
    return results


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
    except ImportError:
        logger.warning("pydub_not_installed", hint="pip install pydub")
        return result  # Fall back to original format
    except Exception as e:
        logger.error("format_conversion_failed", source_format=result.format, target_format=target_format, error=str(e))
        raise
