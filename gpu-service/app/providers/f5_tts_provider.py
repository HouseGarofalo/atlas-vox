"""F5-TTS GPU provider.

Requires ``pip install f5-tts`` or installing from the project repository.
F5-TTS uses flow matching for high-quality zero-shot voice cloning.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import structlog

from app.providers.base import GPUProviderBase

logger = structlog.get_logger(__name__)

try:
    import f5_tts  # type: ignore[import-untyped]  # noqa: F401

    _F5_TTS_AVAILABLE = True
except ImportError:
    _F5_TTS_AVAILABLE = False


class F5TTSProvider(GPUProviderBase):
    """F5-TTS — flow-matching based zero-shot voice cloning."""

    name = "f5_tts"
    display_name = "F5-TTS"

    def __init__(self) -> None:
        self._model: Any = None
        self._device: str = "cuda:0"
        self._cloned_voices: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    def _patch_torchaudio_load() -> None:
        """Monkey-patch torchaudio.load to use soundfile instead of torchcodec.

        On Windows without the ffmpeg shared DLLs, torchcodec fails to load.
        This replaces torchaudio.load with a soundfile-based implementation
        that handles WAV files (which is all F5-TTS needs after pydub
        preprocessing).  Also patches the load_with_torchcodec function to
        prevent direct callers from bypassing the patch.
        """
        try:
            import soundfile as sf
            import torch
            import torchaudio

            def _soundfile_load(
                filepath, frame_offset=0, num_frames=-1, normalize=True,
                channels_first=True, format=None, buffer_size=4096, backend=None,
            ):  # type: ignore[no-untyped-def]
                data, sr = sf.read(str(filepath), dtype="float32")
                if data.ndim == 1:
                    tensor = torch.from_numpy(data).unsqueeze(0)
                else:
                    # (samples, channels) -> (channels, samples)
                    tensor = torch.from_numpy(data.T)
                if not channels_first:
                    tensor = tensor.T
                return tensor, sr

            torchaudio.load = _soundfile_load
            # Also patch the internal function that torchaudio.load delegates to
            if hasattr(torchaudio, "load_with_torchcodec"):
                torchaudio.load_with_torchcodec = _soundfile_load
            if hasattr(torchaudio, "_torchcodec"):
                torchaudio._torchcodec.load_with_torchcodec = _soundfile_load
            logger.info("f5_tts.torchaudio_patched", backend="soundfile")
        except ImportError:
            pass

    def load(self, device: str = "cuda:0") -> None:
        if not _F5_TTS_AVAILABLE:
            raise RuntimeError("f5-tts is not installed. Run: pip install f5-tts")
        self._device = device
        logger.info("f5_tts.loading", device=device)

        # Patch torchaudio before F5-TTS uses it (avoids torchcodec DLL issues)
        self._patch_torchaudio_load()

        try:
            from f5_tts.api import F5TTS  # type: ignore[import-untyped]

            self._model = F5TTS(device=device)
            logger.info("f5_tts.loaded", device=device)
        except Exception as exc:
            logger.error("f5_tts.load_failed", error=str(exc))
            self._model = None
            raise

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            try:
                import torch

                torch.cuda.empty_cache()
            except Exception:
                pass
            logger.info("f5_tts.unloaded")

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        reference_audio: Path | None = None,
    ) -> tuple[np.ndarray, int]:
        self._ensure_loaded()

        ref_path = reference_audio
        if voice_id in self._cloned_voices:
            ref_path = ref_path or Path(self._cloned_voices[voice_id].get("reference", ""))

        if ref_path is None or not ref_path.exists():
            raise ValueError("F5-TTS requires a reference audio file for zero-shot synthesis.")

        try:
            # F5-TTS expects reference audio + reference text for flow matching.
            # When reference text is unknown, pass empty string — the model infers it.
            # infer() returns (wav, sample_rate, spectrogram) — we only need the first two.
            result = self._model.infer(
                ref_file=str(ref_path),
                ref_text="",
                gen_text=text,
                speed=speed,
            )
            audio_array, sr = result[0], result[1]
            return np.asarray(audio_array, dtype=np.float32), int(sr)
        except Exception as exc:
            logger.error("f5_tts.synthesize_failed", error=str(exc))
            raise

    # ------------------------------------------------------------------
    # Voice cloning
    # ------------------------------------------------------------------

    def clone_voice(self, samples: list[Path], name: str = "", language: str = "en") -> dict:
        self._ensure_loaded()
        if not samples:
            raise ValueError("At least one audio sample is required for cloning")

        voice_id = name or f"f5_clone_{len(self._cloned_voices)}"
        self._cloned_voices[voice_id] = {
            "voice_id": voice_id,
            "name": name or voice_id,
            "reference": str(samples[0]),
            "language": language,
            "provider": self.name,
        }
        logger.info("f5_tts.voice_cloned", voice_id=voice_id)
        return self._cloned_voices[voice_id]

    # ------------------------------------------------------------------
    # Voices & capabilities
    # ------------------------------------------------------------------

    def list_voices(self) -> list[dict]:
        return list(self._cloned_voices.values())

    def get_capabilities(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "installed": _F5_TTS_AVAILABLE,
            "is_loaded": self.is_loaded,
            "supports_cloning": True,
            "supports_zero_shot": True,
            "supports_streaming": False,
            "supports_ssml": False,
            "requires_gpu": True,
            "vram_estimate_mb": self.vram_estimate_mb,
            "supported_languages": ["en", "zh"],
            "model": "SWivid/F5-TTS",
        }

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def vram_estimate_mb(self) -> int:
        return 3000

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            raise RuntimeError(
                f"{self.display_name} model is not loaded. Call POST /providers/{self.name}/load first."
            )
