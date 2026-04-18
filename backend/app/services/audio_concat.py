"""Audio concatenation + format conversion helpers for synthesis output.

Extracted from ``synthesis_service`` (P2-17) so the orchestrator stays focused
on coordination rather than numpy / pydub plumbing.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import structlog

from app.core.config import settings
from app.providers.base import AudioResult, SynthesisSettings

logger = structlog.get_logger(__name__)


async def synthesize_and_concat(
    provider,
    chunks: list[str],
    voice_id: str,
    synth_settings: SynthesisSettings,
) -> AudioResult:
    """Synthesize each chunk and concatenate into a single WAV file."""
    import numpy as np
    import soundfile as sf

    all_audio: list = []
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

    return AudioResult(
        audio_path=combined_file,
        duration_seconds=len(combined) / sample_rate,
        sample_rate=sample_rate,
        format="wav",
    )


async def convert_format(result: AudioResult, target_format: str) -> AudioResult:
    """Convert audio to ``target_format`` using pydub (off-loop)."""
    logger.info(
        "format_conversion",
        source_format=result.format,
        target_format=target_format,
        source_path=str(result.audio_path),
    )
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _convert_format_sync, result, target_format)
    except ImportError:
        logger.warning("pydub_not_installed", hint="pip install pydub")
        return result
    except Exception as e:
        logger.error(
            "format_conversion_failed",
            source_format=result.format, target_format=target_format, error=str(e),
        )
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
