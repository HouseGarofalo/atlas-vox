"""Tests for app.services.audio_enhancement (AP-43)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

_HAS_SF = True
_HAS_NR = True
try:  # pragma: no cover - optional import check
    import soundfile as sf  # noqa: F401
except ImportError:
    _HAS_SF = False

try:  # pragma: no cover
    import noisereduce  # noqa: F401
except ImportError:
    _HAS_NR = False


pytestmark = pytest.mark.skipif(
    not (_HAS_SF and _HAS_NR),
    reason="audio-production extras (soundfile + noisereduce) not installed",
)


def _write_wav(path: Path, signal: np.ndarray, sr: int = 16000) -> None:
    import soundfile as sf

    sf.write(str(path), signal.astype(np.float32), sr)


def _rms(signal: np.ndarray) -> float:
    return float(np.sqrt(np.mean(signal.astype(np.float64) ** 2)))


@pytest.fixture
def noisy_wav(tmp_path: Path) -> Path:
    rng = np.random.default_rng(42)
    sr = 16000
    # 1.5s of white noise at 0.2 amplitude
    signal = (rng.standard_normal(sr * 3 // 2) * 0.2).astype(np.float32)
    path = tmp_path / "noise.wav"
    _write_wav(path, signal, sr)
    return path


@pytest.mark.asyncio
async def test_denoise_reduces_rms(noisy_wav: Path, tmp_path: Path):
    from app.services.audio_enhancement import denoise

    import soundfile as sf

    before = _rms(sf.read(str(noisy_wav))[0])
    out = tmp_path / "denoised.wav"
    result = await denoise(noisy_wav, output_path=out, prop_decrease=1.0)
    assert result.exists()
    after = _rms(sf.read(str(result))[0])
    assert after < before, f"RMS should drop after denoise (before={before}, after={after})"


@pytest.mark.asyncio
async def test_dereverb_produces_output(noisy_wav: Path, tmp_path: Path):
    from app.services.audio_enhancement import dereverb

    out = tmp_path / "drv.wav"
    result = await dereverb(noisy_wav, output_path=out, prop_decrease=0.9)
    assert result.exists()
    assert result == out


@pytest.mark.asyncio
async def test_duck_music_lowers_music_during_speech(tmp_path: Path):
    from app.services.audio_enhancement import duck_music

    import soundfile as sf

    sr = 16000
    # Speech mask: silence for 0.5s, then a burst at 0.5s for 0.5s, then silence
    speech = np.zeros(sr * 2, dtype=np.float32)
    speech[sr // 2 : sr] = 0.5  # active region
    # Music: constant 0.4 amplitude
    music = np.ones(sr * 2, dtype=np.float32) * 0.4

    speech_path = tmp_path / "speech.wav"
    music_path = tmp_path / "music.wav"
    _write_wav(speech_path, speech, sr)
    _write_wav(music_path, music, sr)

    out = tmp_path / "ducked.wav"
    result = await duck_music(
        speech_path, music_path, output_path=out, speech_duck_db=-18.0
    )
    assert result.exists()

    mixed, _sr = sf.read(str(result))
    mixed = np.asarray(mixed, dtype=np.float64)

    # During speech interval (0.5s - 1.0s), most of signal should be the
    # speech at 0.5 + a quiet music floor.  Outside, it should equal the
    # un-ducked music (~0.4).
    active = mixed[sr // 2 + 200 : sr - 200]
    silent = mixed[sr + 200 : 2 * sr - 200]

    # The speech in active region dominates, so measurement uses ducked music
    # + speech.  What we assert: music-only silent region has HIGHER RMS than
    # speech-minus-speech residual in the active region.
    # Subtract speech to isolate the ducked music component.
    speech_active = speech[sr // 2 + 200 : sr - 200].astype(np.float64)
    music_component_during_speech = active - speech_active
    silent_rms = _rms(silent)
    ducked_rms = _rms(music_component_during_speech)
    assert ducked_rms < silent_rms, (
        f"Ducked music ({ducked_rms}) should be quieter than silent-region music "
        f"({silent_rms})."
    )


@pytest.mark.asyncio
async def test_duck_music_rejects_positive_db(tmp_path: Path):
    from app.services.audio_enhancement import duck_music

    sr = 16000
    speech_path = tmp_path / "s.wav"
    music_path = tmp_path / "m.wav"
    _write_wav(speech_path, np.zeros(sr, dtype=np.float32), sr)
    _write_wav(music_path, np.zeros(sr, dtype=np.float32), sr)

    with pytest.raises(ValueError):
        await duck_music(speech_path, music_path, speech_duck_db=3.0)
