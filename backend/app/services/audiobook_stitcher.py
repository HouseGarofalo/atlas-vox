"""Audiobook / long-form stitcher.

Pipeline
--------
1.  Parse markdown into chapters (``#`` / ``##``) and paragraphs.
2.  For each paragraph compile an SSML fragment via
    :func:`app.services.markdown_to_ssml.compile_to_ssml`, respecting the
    active provider's capabilities.
3.  Synthesize each paragraph via :func:`synthesis_service.synthesize`.
4.  Concatenate the paragraph audio with a short crossfade.
5.  Loudness-normalize to LUFS -16 via ``pyloudnorm`` (with a peak-normalize
    fallback if pyloudnorm is unavailable).
6.  Produce an MP3 and a list of chapter markers.

The rendering is synchronous from the caller's perspective — it awaits all
steps before returning.  Background scheduling can be layered on later.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.voice_profile import VoiceProfile
from app.services.markdown_to_ssml import compile_to_ssml
from app.services.provider_registry import provider_registry

logger = structlog.get_logger(__name__)

CROSSFADE_MS_DEFAULT = 300
TARGET_LUFS_DEFAULT = -16.0


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ChapterMarker:
    """A single chapter marker in the rendered audiobook."""

    index: int
    title: str
    start_seconds: float
    end_seconds: float


@dataclass
class AudiobookResult:
    """Outcome of a render_audiobook call."""

    output_path: Path
    duration_seconds: float
    chapter_markers: list[ChapterMarker] = field(default_factory=list)
    paragraph_count: int = 0
    loudness_lufs: float | None = None
    loudness_fallback: bool = False


@dataclass
class _Chapter:
    """Internal chapter representation used by :func:`parse_markdown`."""

    title: str
    paragraphs: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^\s{0,3}(#{1,2})\s+(.*?)\s*$")


def parse_markdown(markdown: str) -> list[_Chapter]:
    """Split markdown into chapters by ``#``/``##`` headings.

    The first run of paragraphs before any heading is collected into an
    "Untitled" chapter so no content is dropped.
    """
    chapters: list[_Chapter] = []
    current = _Chapter(title="Untitled")
    buf: list[str] = []

    def flush_paragraph() -> None:
        if buf:
            para = "\n".join(buf).strip()
            if para:
                current.paragraphs.append(para)
            buf.clear()

    lines = markdown.splitlines()
    for line in lines:
        heading = _HEADING_RE.match(line)
        if heading is not None:
            flush_paragraph()
            # Commit the pending chapter if it has any content or a title
            # that was actually set (don't leave an empty "Untitled" shell).
            if current.paragraphs or current.title != "Untitled" or chapters:
                chapters.append(current)
            current = _Chapter(title=heading.group(2).strip() or "Untitled")
            continue

        if not line.strip():
            flush_paragraph()
        else:
            buf.append(line)

    flush_paragraph()
    if current.paragraphs or not chapters:
        chapters.append(current)

    # Strip leading placeholder chapter if empty AND we already have real ones.
    if len(chapters) > 1 and not chapters[0].paragraphs and chapters[0].title == "Untitled":
        chapters = chapters[1:]

    return chapters


# ---------------------------------------------------------------------------
# Audio helpers (all synchronous — run in executors)
# ---------------------------------------------------------------------------

def _concat_with_crossfade_sync(audio_paths: list[Path], crossfade_ms: int, out_path: Path) -> Path:
    """Concatenate audio segments with a crossfade using pydub."""
    from pydub import AudioSegment

    if not audio_paths:
        raise ValueError("Cannot concatenate an empty audio list")

    combined: AudioSegment | None = None
    for path in audio_paths:
        seg = AudioSegment.from_file(str(path))
        if combined is None:
            combined = seg
        else:
            effective = min(crossfade_ms, len(combined), len(seg))
            if effective <= 0:
                combined = combined + seg
            else:
                combined = combined.append(seg, crossfade=effective)

    assert combined is not None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.export(str(out_path), format="wav")
    return out_path


def _loudness_normalize_sync(audio_path: Path, out_path: Path, target_lufs: float) -> tuple[Path, float | None, bool]:
    """Normalize to target LUFS using pyloudnorm; fall back to peak-normalize.

    Returns (output_path, measured_lufs, used_fallback).
    """
    import numpy as np
    import soundfile as sf

    data, sr = sf.read(str(audio_path))
    if data.size == 0:
        raise ValueError(f"Audio file is empty: {audio_path}")

    measured: float | None = None
    used_fallback = False
    try:
        import pyloudnorm as pyln

        meter = pyln.Meter(sr)
        measured = float(meter.integrated_loudness(data))
        # pyloudnorm defines normalize.loudness; returns an ndarray
        normalized = pyln.normalize.loudness(data, measured, target_lufs)
    except ImportError:
        used_fallback = True
        logger.warning("pyloudnorm_not_installed", hint="pip install pyloudnorm")
        peak = float(np.max(np.abs(data)))
        if peak > 0:
            normalized = data * (0.95 / peak)
        else:
            normalized = data
    except Exception as exc:  # pragma: no cover - pyloudnorm edge cases
        used_fallback = True
        logger.warning("loudness_normalize_failed", error=str(exc))
        peak = float(np.max(np.abs(data)))
        if peak > 0:
            normalized = data * (0.95 / peak)
        else:
            normalized = data

    # Clip to [-1, 1] defensively (pyloudnorm can overshoot).
    max_abs = float(np.max(np.abs(normalized)))
    if max_abs > 1.0:
        normalized = normalized / max_abs

    sf.write(str(out_path), normalized, sr)
    return out_path, measured, used_fallback


def _encode_mp3_sync(wav_path: Path, mp3_path: Path) -> Path:
    from pydub import AudioSegment

    audio = AudioSegment.from_file(str(wav_path))
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    audio.export(str(mp3_path), format="mp3", bitrate="128k")
    return mp3_path


def _duration_seconds_sync(audio_path: Path) -> float:
    import soundfile as sf

    with sf.SoundFile(str(audio_path)) as f:
        return len(f) / float(f.samplerate)


# ---------------------------------------------------------------------------
# Async wrappers
# ---------------------------------------------------------------------------

async def _run_sync(func, /, *args, **kwargs):
    loop = asyncio.get_event_loop()
    if kwargs:
        from functools import partial as _partial
        return await loop.run_in_executor(None, _partial(func, *args, **kwargs))
    return await loop.run_in_executor(None, func, *args)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def render_audiobook(
    db: AsyncSession,
    project_id: str | None,
    markdown: str,
    profile_id: str,
    options: dict[str, Any] | None = None,
) -> AudiobookResult:
    """Render a long-form audiobook from markdown using the given voice profile.

    Args:
        db: Active DB session (used for profile lookups and synthesis).
        project_id: Optional project tag used only in log lines at the moment.
        markdown: Input manuscript in markdown with optional Atlas Vox directives.
        profile_id: Voice profile to synthesize with.
        options: Optional knobs:
            - ``crossfade_ms`` (int, default 300)
            - ``target_lufs`` (float, default -16.0)
            - ``output_format`` (str, default "mp3")
            - ``preset_id`` (str, optional)
    """
    opts = options or {}
    crossfade_ms = int(opts.get("crossfade_ms", CROSSFADE_MS_DEFAULT))
    target_lufs = float(opts.get("target_lufs", TARGET_LUFS_DEFAULT))
    output_format = str(opts.get("output_format", "mp3")).lower()
    preset_id = opts.get("preset_id")

    # ---- Lookup profile + capabilities ----------------------------------
    profile_result = await db.execute(
        select(VoiceProfile).where(VoiceProfile.id == profile_id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Profile", profile_id)

    provider = provider_registry.get_provider(profile.provider_name)
    capabilities = await provider.get_capabilities()

    # ---- Chapter + paragraph parsing ------------------------------------
    chapters = parse_markdown(markdown)
    paragraph_count = sum(len(c.paragraphs) for c in chapters)
    if paragraph_count == 0:
        raise ValueError("Markdown contains no renderable paragraphs")

    logger.info(
        "audiobook_render_start",
        project_id=project_id,
        profile_id=profile_id,
        provider=profile.provider_name,
        chapter_count=len(chapters),
        paragraph_count=paragraph_count,
        target_lufs=target_lufs,
        crossfade_ms=crossfade_ms,
    )

    # ---- Per-paragraph synthesis ----------------------------------------
    # Import here to allow test-time monkeypatch of the name inside this module.
    from app.services import synthesis_service

    paragraph_audio_paths: list[Path] = []
    paragraph_durations: list[float] = []
    chapter_paragraph_spans: list[tuple[int, int]] = []  # (start_idx, end_idx) inclusive

    running_index = 0
    for chapter in chapters:
        start = running_index
        for paragraph in chapter.paragraphs:
            ssml = compile_to_ssml(paragraph, capabilities)
            result = await synthesis_service.synthesize(
                db,
                text=ssml,
                profile_id=profile_id,
                preset_id=preset_id,
                output_format="wav",
                ssml=capabilities.supports_ssml,
            )
            audio_url = result.get("audio_url") or ""
            filename = Path(audio_url).name
            audio_path = Path(settings.storage_path) / "output" / filename
            if not audio_path.exists():
                # fall back to any absolute path that might be returned
                alt = result.get("output_path")
                if alt and Path(alt).exists():
                    audio_path = Path(alt)
            paragraph_audio_paths.append(audio_path)
            paragraph_durations.append(float(result.get("duration_seconds") or 0.0))
            running_index += 1
        end = running_index - 1
        chapter_paragraph_spans.append((start, end))

    # ---- Concatenation with crossfade ------------------------------------
    output_dir = Path(settings.storage_path) / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    concat_wav = output_dir / f"audiobook_concat_{uuid.uuid4().hex[:12]}.wav"
    await _run_sync(_concat_with_crossfade_sync, paragraph_audio_paths, crossfade_ms, concat_wav)

    # ---- Loudness normalization -----------------------------------------
    loud_wav = output_dir / f"audiobook_loud_{uuid.uuid4().hex[:12]}.wav"
    _, measured_lufs, fallback = await _run_sync(
        _loudness_normalize_sync, concat_wav, loud_wav, target_lufs
    )

    # ---- Final encoding --------------------------------------------------
    if output_format == "mp3":
        final_path = output_dir / f"audiobook_{uuid.uuid4().hex[:12]}.mp3"
        await _run_sync(_encode_mp3_sync, loud_wav, final_path)
    else:
        final_path = output_dir / f"audiobook_{uuid.uuid4().hex[:12]}.wav"
        # Keep the loud_wav as the final file.
        loud_wav.rename(final_path)

    # ---- Chapter markers -------------------------------------------------
    # Timings are based on nominal paragraph durations.  The crossfade trims
    # (n-1) * crossfade_ms from the combined timeline so we distribute it
    # across the boundaries to keep markers inside the final file.
    crossfade_s = crossfade_ms / 1000.0
    cum = 0.0
    paragraph_starts: list[float] = []
    paragraph_ends: list[float] = []
    for idx, dur in enumerate(paragraph_durations):
        start = cum
        end = cum + dur
        # shift subsequent segments back by the crossfade overlap
        cum = end - (crossfade_s if idx < len(paragraph_durations) - 1 else 0.0)
        paragraph_starts.append(start)
        paragraph_ends.append(max(end, start))

    markers: list[ChapterMarker] = []
    for idx, chapter in enumerate(chapters):
        start_idx, end_idx = chapter_paragraph_spans[idx]
        if not chapter.paragraphs:
            continue
        markers.append(
            ChapterMarker(
                index=idx,
                title=chapter.title,
                start_seconds=round(paragraph_starts[start_idx], 3),
                end_seconds=round(paragraph_ends[end_idx], 3),
            )
        )

    total_duration = await _run_sync(_duration_seconds_sync, final_path)

    # Cleanup intermediates (best-effort)
    for tmp in (concat_wav, loud_wav):
        try:
            if tmp.exists() and tmp != final_path:
                tmp.unlink()
        except OSError:
            logger.warning("audiobook_cleanup_failed", path=str(tmp))

    logger.info(
        "audiobook_render_complete",
        project_id=project_id,
        profile_id=profile_id,
        output=str(final_path),
        duration_seconds=total_duration,
        chapters=len(markers),
        loudness_fallback=fallback,
        measured_lufs=measured_lufs,
    )

    return AudiobookResult(
        output_path=final_path,
        duration_seconds=total_duration,
        chapter_markers=markers,
        paragraph_count=paragraph_count,
        loudness_lufs=measured_lufs,
        loudness_fallback=fallback,
    )


__all__ = [
    "AudiobookResult",
    "ChapterMarker",
    "parse_markdown",
    "render_audiobook",
]
