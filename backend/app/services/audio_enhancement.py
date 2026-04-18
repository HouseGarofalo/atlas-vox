"""Audio post-processing helpers: denoise, de-reverb, music ducking.

All heavy work runs in a thread executor to keep the FastAPI event loop free.
Dependencies are imported lazily so the module can be imported even when the
optional ``audio-production`` extras are not installed — functions raise
``RuntimeError`` with a helpful message instead.
"""

from __future__ import annotations

import asyncio
import uuid
from functools import partial
from pathlib import Path

import numpy as np
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _output_dir() -> Path:
    out = Path(settings.storage_path) / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _new_output_path(prefix: str, ext: str = "wav") -> Path:
    return _output_dir() / f"{prefix}_{uuid.uuid4().hex[:12]}.{ext}"


def _require_noisereduce():
    try:
        import noisereduce as nr
    except ImportError as exc:  # pragma: no cover - exercised only without extras
        raise RuntimeError(
            "noisereduce is not installed — add the 'audio-production' extras "
            "or install noisereduce manually."
        ) from exc
    return nr


def _require_soundfile_librosa():
    try:
        import librosa  # noqa: F401
        import soundfile as sf  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "librosa and soundfile are required for audio enhancement."
        ) from exc
    return True


# ---------------------------------------------------------------------------
# Denoise
# ---------------------------------------------------------------------------

def _denoise_sync(audio_path: Path, output_path: Path, prop_decrease: float) -> Path:
    import librosa
    import soundfile as sf

    nr = _require_noisereduce()
    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    if len(y) == 0:
        raise ValueError(f"Audio file is empty: {audio_path}")

    reduced = nr.reduce_noise(y=y, sr=sr, prop_decrease=prop_decrease)
    sf.write(str(output_path), reduced, sr)
    return output_path


async def denoise(
    audio_path: Path,
    output_path: Path | None = None,
    prop_decrease: float = 0.85,
) -> Path:
    """Reduce broadband noise on ``audio_path`` using noisereduce.

    Args:
        audio_path: Path to the noisy input file.
        output_path: Optional destination; a unique path is allocated otherwise.
        prop_decrease: How aggressively to reduce noise (0-1).

    Returns:
        Path to the denoised WAV file.
    """
    _require_soundfile_librosa()
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    dest = output_path or _new_output_path("denoise")
    logger.info("denoise_start", src=str(audio_path), dst=str(dest))

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(_denoise_sync, audio_path, dest, prop_decrease)
    )


# ---------------------------------------------------------------------------
# De-reverb (approximated via stationary spectral gating)
# ---------------------------------------------------------------------------

def _dereverb_sync(audio_path: Path, output_path: Path, prop_decrease: float) -> Path:
    import librosa
    import soundfile as sf

    nr = _require_noisereduce()
    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    if len(y) == 0:
        raise ValueError(f"Audio file is empty: {audio_path}")

    # Stationary mode treats the reverb tail as a stationary noise floor,
    # which is a coarse but effective approximation for light rooms.
    reduced = nr.reduce_noise(
        y=y,
        sr=sr,
        stationary=True,
        prop_decrease=prop_decrease,
    )
    sf.write(str(output_path), reduced, sr)
    return output_path


async def dereverb(
    audio_path: Path,
    output_path: Path | None = None,
    prop_decrease: float = 0.95,
) -> Path:
    """Reduce light reverberation via stationary spectral gating."""
    _require_soundfile_librosa()
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    dest = output_path or _new_output_path("dereverb")
    logger.info("dereverb_start", src=str(audio_path), dst=str(dest))

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(_dereverb_sync, audio_path, dest, prop_decrease)
    )


# ---------------------------------------------------------------------------
# Music ducking
# ---------------------------------------------------------------------------

def _frame_rms(signal: np.ndarray, frame_size: int) -> np.ndarray:
    """Compute per-frame RMS for a mono signal."""
    if len(signal) == 0:
        return np.zeros(0, dtype=np.float64)
    pad = frame_size - (len(signal) % frame_size)
    if pad and pad != frame_size:
        signal = np.concatenate([signal, np.zeros(pad, dtype=signal.dtype)])
    frames = signal.reshape(-1, frame_size)
    return np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))


def _detect_speech_mask(
    speech: np.ndarray,
    sr: int,
    frame_ms: int = 20,
    threshold_rel_db: float = -30.0,
    smoothing_frames: int = 10,
) -> np.ndarray:
    """Return a boolean mask (length == len(speech)) marking speech frames."""
    if len(speech) == 0:
        return np.zeros(0, dtype=bool)

    frame_size = max(1, int(sr * frame_ms / 1000))
    rms = _frame_rms(speech, frame_size)
    if rms.size == 0:
        return np.zeros(len(speech), dtype=bool)

    peak = float(rms.max())
    if peak <= 0:
        return np.zeros(len(speech), dtype=bool)

    # Convert threshold dB to linear, relative to peak.
    threshold = peak * (10.0 ** (threshold_rel_db / 20.0))
    frame_mask = rms >= threshold

    # Smooth the mask so we don't duck for every sub-word silence gap.
    if smoothing_frames > 1 and frame_mask.size:
        kernel = np.ones(smoothing_frames) / smoothing_frames
        smoothed = np.convolve(frame_mask.astype(np.float64), kernel, mode="same")
        frame_mask = smoothed > 0.3

    # Expand frame-level mask back to per-sample.
    sample_mask = np.repeat(frame_mask, frame_size)[: len(speech)]
    if len(sample_mask) < len(speech):
        pad = np.zeros(len(speech) - len(sample_mask), dtype=bool)
        sample_mask = np.concatenate([sample_mask, pad])
    return sample_mask


def _duck_sync(
    speech_path: Path,
    music_path: Path,
    output_path: Path,
    speech_duck_db: float,
    frame_ms: int,
) -> Path:
    import librosa
    import soundfile as sf

    speech, sr = librosa.load(str(speech_path), sr=None, mono=True)
    music, music_sr = librosa.load(str(music_path), sr=None, mono=True)

    if len(speech) == 0:
        raise ValueError(f"Speech file is empty: {speech_path}")
    if len(music) == 0:
        raise ValueError(f"Music file is empty: {music_path}")

    # Resample music to match speech rate.
    if music_sr != sr:
        music = librosa.resample(music, orig_sr=music_sr, target_sr=sr)

    # Pad/truncate music to match speech length.
    if len(music) < len(speech):
        reps = int(np.ceil(len(speech) / len(music)))
        music = np.tile(music, reps)[: len(speech)]
    else:
        music = music[: len(speech)]

    mask = _detect_speech_mask(speech, sr, frame_ms=frame_ms)

    duck_linear = 10.0 ** (speech_duck_db / 20.0)
    gains = np.where(mask, duck_linear, 1.0).astype(np.float64)

    # Short fade on gain changes so ducking doesn't click.
    fade_samples = max(1, int(sr * 0.02))
    kernel = np.ones(fade_samples) / fade_samples
    gains = np.convolve(gains, kernel, mode="same")

    ducked_music = music.astype(np.float64) * gains
    mixed = speech.astype(np.float64) + ducked_music

    # Avoid clipping.
    peak = float(np.max(np.abs(mixed))) or 1.0
    if peak > 1.0:
        mixed = mixed / peak

    sf.write(str(output_path), mixed.astype(np.float32), sr)
    return output_path


async def duck_music(
    speech_path: Path,
    music_path: Path,
    output_path: Path | None = None,
    speech_duck_db: float = -18.0,
    frame_ms: int = 20,
) -> Path:
    """Mix speech and music, lowering music by ``speech_duck_db`` during speech.

    Args:
        speech_path: The speech / narration track.
        music_path: The background music track (looped or truncated to match).
        output_path: Optional destination; unique WAV allocated otherwise.
        speech_duck_db: Amount (in dB, negative) to attenuate music during speech.
        frame_ms: Analysis frame size for RMS-based speech detection.

    Returns:
        Path to the mixed WAV file.
    """
    _require_soundfile_librosa()
    if not speech_path.exists():
        raise FileNotFoundError(f"Speech file not found: {speech_path}")
    if not music_path.exists():
        raise FileNotFoundError(f"Music file not found: {music_path}")
    if speech_duck_db > 0:
        raise ValueError("speech_duck_db must be <= 0 (attenuation)")

    dest = output_path or _new_output_path("ducked")
    logger.info(
        "duck_music_start",
        speech=str(speech_path),
        music=str(music_path),
        dst=str(dest),
        duck_db=speech_duck_db,
    )

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        partial(_duck_sync, speech_path, music_path, dest, speech_duck_db, frame_ms),
    )


__all__ = [
    "denoise",
    "dereverb",
    "duck_music",
    "_detect_speech_mask",
    "_frame_rms",
]
