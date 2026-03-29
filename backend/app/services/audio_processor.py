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
