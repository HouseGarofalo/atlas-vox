"""Fish Speech 1.5 GPU provider.

Requires ``pip install fish-speech``.  When the package is not installed the
provider will still load but report ``installed: false`` in its capabilities.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import structlog

from app.providers.base import GPUProviderBase

logger = structlog.get_logger(__name__)

# Attempt to import the library at module level so we can gate functionality.
try:
    import fish_speech  # noqa: F401

    _FISH_SPEECH_AVAILABLE = True
except ImportError:
    _FISH_SPEECH_AVAILABLE = False


class FishSpeechProvider(GPUProviderBase):
    """Fish Speech 1.5 — multilingual TTS with zero-shot voice cloning.

    Model: ``fishaudio/fish-speech-1.5`` (HuggingFace).
    """

    name = "fish_speech"
    display_name = "Fish Speech 1.5"

    def __init__(self) -> None:
        self._model: Any = None
        self._device: str = "cuda:0"
        self._cloned_voices: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self, device: str = "cuda:0") -> None:
        if not _FISH_SPEECH_AVAILABLE:
            raise RuntimeError("fish-speech is not installed. Run: pip install fish-speech")
        self._device = device
        logger.info("fish_speech.loading", device=device)
        try:
            # Fish Speech API — load the model onto the target device.
            from fish_speech.models import TTSModel  # type: ignore[import-untyped]

            self._model = TTSModel.from_pretrained("fishaudio/fish-speech-1.5", device=device)
            logger.info("fish_speech.loaded", device=device)
        except Exception as exc:
            logger.error("fish_speech.load_failed", error=str(exc))
            self._model = None
            raise

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            # Attempt to reclaim VRAM.
            try:
                import torch

                torch.cuda.empty_cache()
            except Exception:
                pass
            logger.info("fish_speech.unloaded")

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

        try:
            audio_array, sr = self._model.synthesize(
                text=text,
                reference_audio=str(ref_path) if ref_path else None,
                speed=speed,
            )
            return np.asarray(audio_array, dtype=np.float32), int(sr)
        except Exception as exc:
            logger.error("fish_speech.synthesize_failed", error=str(exc))
            raise

    # ------------------------------------------------------------------
    # Voice cloning
    # ------------------------------------------------------------------

    def clone_voice(self, samples: list[Path], name: str = "", language: str = "en") -> dict:
        self._ensure_loaded()
        if not samples:
            raise ValueError("At least one audio sample is required for cloning")

        voice_id = name or f"fish_clone_{len(self._cloned_voices)}"
        # Fish Speech uses zero-shot cloning — store the reference audio path.
        self._cloned_voices[voice_id] = {
            "voice_id": voice_id,
            "name": name or voice_id,
            "reference": str(samples[0]),
            "language": language,
            "provider": self.name,
        }
        logger.info("fish_speech.voice_cloned", voice_id=voice_id)
        return self._cloned_voices[voice_id]

    # ------------------------------------------------------------------
    # Voices & capabilities
    # ------------------------------------------------------------------

    def list_voices(self) -> list[dict]:
        voices: list[dict] = [
            {
                "voice_id": "default",
                "name": "Fish Speech Default",
                "language": "en",
                "provider": self.name,
            }
        ]
        voices.extend(self._cloned_voices.values())
        return voices

    def get_capabilities(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "installed": _FISH_SPEECH_AVAILABLE,
            "is_loaded": self.is_loaded,
            "supports_cloning": True,
            "supports_zero_shot": True,
            "supports_streaming": False,
            "supports_ssml": False,
            "requires_gpu": True,
            "vram_estimate_mb": self.vram_estimate_mb,
            "supported_languages": ["en", "zh", "ja", "ko", "fr", "de", "es"],
            "model": "fishaudio/fish-speech-1.5",
        }

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def vram_estimate_mb(self) -> int:
        return 4000

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            raise RuntimeError(f"{self.display_name} model is not loaded. Call POST /providers/{self.name}/load first.")
