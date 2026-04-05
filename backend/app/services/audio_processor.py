"""Audio preprocessing and analysis pipeline.

Used by all providers before training — normalizes, denoises, and converts
audio to a standard format (WAV 16kHz mono).
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from functools import partial
from pathlib import Path

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PreprocessConfig:
    """Configuration for audio preprocessing."""

    target_sample_rate: int = 16000
    target_format: str = "wav"
    noise_reduction_strength: float = 0.5
    silence_threshold_db: float = -40.0
    normalize: bool = True
    trim_silence: bool = True


@dataclass
class AudioAnalysis:
    """Result of audio analysis."""

    duration_seconds: float = 0.0
    sample_rate: int = 0
    pitch_mean: float | None = None
    pitch_std: float | None = None
    energy_mean: float | None = None
    energy_std: float | None = None
    spectral_centroid_mean: float | None = None
    rms_db: float | None = None

    def to_json(self) -> str:
        return json.dumps({
            "duration_seconds": self.duration_seconds,
            "sample_rate": self.sample_rate,
            "pitch_mean": self.pitch_mean,
            "pitch_std": self.pitch_std,
            "energy_mean": self.energy_mean,
            "energy_std": self.energy_std,
            "spectral_centroid_mean": self.spectral_centroid_mean,
            "rms_db": self.rms_db,
        })


def _preprocess_sync(
    input_path: Path, output_path: Path, config: PreprocessConfig
) -> Path:
    """Synchronous audio preprocessing (runs in executor)."""
    import librosa
    import soundfile as sf

    # Load audio at original sample rate
    y, sr = librosa.load(str(input_path), sr=None, mono=True)

    if len(y) == 0:
        raise ValueError(f"Audio file is empty: {input_path}")

    # Noise reduction (optional, uses noisereduce if available)
    if config.noise_reduction_strength > 0:
        try:
            import noisereduce as nr

            y = nr.reduce_noise(
                y=y,
                sr=sr,
                prop_decrease=config.noise_reduction_strength,
            )
        except ImportError:
            logger.warning("noisereduce_not_installed", hint="pip install noisereduce")

    # Trim silence from beginning and end
    if config.trim_silence:
        y, _ = librosa.effects.trim(y, top_db=abs(config.silence_threshold_db))

    # Normalize amplitude to [-1, 1]
    if config.normalize:
        peak = np.max(np.abs(y))
        if peak > 0:
            y = y / peak

    # Resample to target rate
    if sr != config.target_sample_rate:
        y = librosa.resample(y, orig_sr=sr, target_sr=config.target_sample_rate)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), y, config.target_sample_rate, subtype="PCM_16")

    logger.info(
        "audio_preprocessed",
        input=str(input_path),
        output=str(output_path),
        original_sr=sr,
        target_sr=config.target_sample_rate,
        duration_s=round(len(y) / config.target_sample_rate, 2),
    )
    return output_path


def _analyze_sync(path: Path) -> AudioAnalysis:
    """Synchronous audio analysis (runs in executor)."""
    import librosa

    y, sr = librosa.load(str(path), sr=None, mono=True)

    if len(y) == 0:
        return AudioAnalysis(duration_seconds=0.0, sample_rate=sr)

    duration = len(y) / sr

    # Pitch (F0) via pyin
    f0, voiced_flag, _ = librosa.pyin(
        y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr
    )
    f0_valid = f0[~np.isnan(f0)] if f0 is not None else np.array([])

    # Energy (RMS)
    rms = librosa.feature.rms(y=y)[0]

    # Spectral centroid
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]

    # Overall RMS in dB
    rms_total = np.sqrt(np.mean(y**2))
    rms_db = float(20 * np.log10(rms_total + 1e-10))

    return AudioAnalysis(
        duration_seconds=round(duration, 3),
        sample_rate=sr,
        pitch_mean=round(float(np.mean(f0_valid)), 2) if len(f0_valid) > 0 else None,
        pitch_std=round(float(np.std(f0_valid)), 2) if len(f0_valid) > 0 else None,
        energy_mean=round(float(np.mean(rms)), 6),
        energy_std=round(float(np.std(rms)), 6),
        spectral_centroid_mean=round(float(np.mean(spectral_centroid)), 2),
        rms_db=round(rms_db, 2),
    )


async def preprocess_audio(
    input_path: Path, output_path: Path, config: PreprocessConfig | None = None
) -> Path:
    """Preprocess an audio file (async wrapper — runs CPU work in executor)."""
    if config is None:
        config = PreprocessConfig()

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, partial(_preprocess_sync, input_path, output_path, config)
    )


async def analyze_audio(path: Path) -> AudioAnalysis:
    """Analyze an audio file and return pitch/energy/spectral metrics."""
    logger.info("audio_analysis_started", path=str(path))
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, partial(_analyze_sync, path))
    logger.info(
        "audio_analysis_completed",
        path=str(path),
        duration_seconds=result.duration_seconds,
        sample_rate=result.sample_rate,
        rms_db=result.rms_db,
    )
    return result


# ---------------------------------------------------------------------------
# Audio Design Studio helpers
# ---------------------------------------------------------------------------


def _trim_sync(input_path: Path, output_path: Path, start: float, end: float) -> Path:
    """Trim audio to [start, end] seconds."""
    import librosa
    import soundfile as sf

    y, sr = librosa.load(str(input_path), sr=None, mono=True)
    start_sample = int(start * sr)
    end_sample = int(end * sr)
    end_sample = min(end_sample, len(y))
    if start_sample >= end_sample:
        raise ValueError(f"Invalid trim range: {start}s - {end}s (duration {len(y) / sr:.2f}s)")

    y_trimmed = y[start_sample:end_sample]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), y_trimmed, sr, subtype="PCM_16")
    logger.info("audio_trimmed", input=str(input_path), start=start, end=end, output=str(output_path))
    return output_path


def _concat_sync(input_paths: list[Path], output_path: Path, crossfade_ms: int = 0) -> Path:
    """Concatenate multiple audio files, optionally with crossfade."""
    import librosa
    import soundfile as sf

    segments: list[np.ndarray] = []
    target_sr: int | None = None

    for p in input_paths:
        y, sr = librosa.load(str(p), sr=None, mono=True)
        if target_sr is None:
            target_sr = sr
        elif sr != target_sr:
            y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
        segments.append(y)

    if not segments or target_sr is None:
        raise ValueError("No audio segments to concatenate")

    if crossfade_ms > 0 and len(segments) > 1:
        crossfade_samples = int(crossfade_ms / 1000.0 * target_sr)
        result = segments[0]
        for seg in segments[1:]:
            overlap = min(crossfade_samples, len(result), len(seg))
            if overlap > 0:
                fade_out = np.linspace(1.0, 0.0, overlap)
                fade_in = np.linspace(0.0, 1.0, overlap)
                result[-overlap:] = result[-overlap:] * fade_out + seg[:overlap] * fade_in
                result = np.concatenate([result, seg[overlap:]])
            else:
                result = np.concatenate([result, seg])
    else:
        result = np.concatenate(segments)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), result, target_sr, subtype="PCM_16")
    logger.info("audio_concatenated", file_count=len(input_paths), output=str(output_path))
    return output_path


def _apply_gain_sync(input_path: Path, output_path: Path, gain_db: float) -> Path:
    """Apply gain (volume adjustment) in dB."""
    import librosa
    import soundfile as sf

    y, sr = librosa.load(str(input_path), sr=None, mono=True)
    gain_linear = 10 ** (gain_db / 20.0)
    y = y * gain_linear
    y = np.clip(y, -1.0, 1.0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), y, sr, subtype="PCM_16")
    logger.info("audio_gain_applied", gain_db=gain_db, output=str(output_path))
    return output_path


def _convert_format_sync(input_path: Path, output_path: Path, target_format: str, target_sr: int | None = None) -> Path:
    """Convert audio to a different format and/or sample rate."""
    from pydub import AudioSegment

    audio = AudioSegment.from_file(str(input_path))

    if target_sr:
        audio = audio.set_frame_rate(target_sr)

    audio = audio.set_channels(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    format_map = {"wav": "wav", "mp3": "mp3", "ogg": "ogg", "flac": "flac"}
    fmt = format_map.get(target_format.lower(), "wav")
    sf_path = output_path.with_suffix(f".{fmt}")
    audio.export(str(sf_path), format=fmt)
    logger.info("audio_format_converted", format=fmt, sample_rate=target_sr, output=str(sf_path))
    return sf_path


def _get_audio_info_sync(path: Path) -> dict:
    """Get audio file metadata without full analysis."""
    import librosa

    y, sr = librosa.load(str(path), sr=None, mono=True)
    return {
        "duration_seconds": round(len(y) / sr, 3),
        "sample_rate": sr,
        "channels": 1,
        "format": path.suffix.lstrip(".").lower(),
        "file_size_bytes": path.stat().st_size,
    }


async def trim_audio(input_path: Path, output_path: Path, start: float, end: float) -> Path:
    """Trim audio to [start, end] seconds (async)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_trim_sync, input_path, output_path, start, end))


async def concat_audio(input_paths: list[Path], output_path: Path, crossfade_ms: int = 0) -> Path:
    """Concatenate multiple audio files (async)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_concat_sync, input_paths, output_path, crossfade_ms))


async def apply_gain(input_path: Path, output_path: Path, gain_db: float) -> Path:
    """Apply gain adjustment (async)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_apply_gain_sync, input_path, output_path, gain_db))


async def convert_format(input_path: Path, output_path: Path, target_format: str, target_sr: int | None = None) -> Path:
    """Convert audio format and/or sample rate (async)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_convert_format_sync, input_path, output_path, target_format, target_sr))


async def get_audio_info(path: Path) -> dict:
    """Get audio file metadata (async)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_get_audio_info_sync, path))
