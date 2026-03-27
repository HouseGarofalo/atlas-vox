"""Orpheus TTS GPU provider.

Orpheus is a Llama-3B based TTS model that supports zero-shot voice cloning
and emotion control via inline tags (e.g. ``<laugh>``, ``<sigh>``).  It uses
Unsloth for efficient fine-tuning.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import structlog

from app.providers.base import GPUProviderBase

logger = structlog.get_logger(__name__)

try:
    from orpheus_tts import OrpheusModel  # type: ignore[import-untyped]

    _ORPHEUS_AVAILABLE = True
except ImportError:
    _ORPHEUS_AVAILABLE = False
    OrpheusModel = None  # type: ignore[assignment,misc]


class OrpheusProvider(GPUProviderBase):
    """Orpheus TTS — Llama-3B based expressive speech synthesis with emotion tags."""

    name = "orpheus"
    display_name = "Orpheus TTS"

    EMOTION_TAGS = ["<laugh>", "<sigh>", "<gasp>", "<cough>", "<clears_throat>", "<singing>", "<whisper>"]

    def __init__(self) -> None:
        self._model: Any = None
        self._device: str = "cuda:0"
        self._cloned_voices: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self, device: str = "cuda:0") -> None:
        if not _ORPHEUS_AVAILABLE:
            raise RuntimeError("orpheus-tts is not installed. See the Orpheus TTS repository for installation.")
        self._device = device
        logger.info("orpheus.loading", device=device)
        try:
            self._model = OrpheusModel.from_pretrained(device=device)
            logger.info("orpheus.loaded", device=device)
        except Exception as exc:
            logger.error("orpheus.load_failed", error=str(exc))
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
            logger.info("orpheus.unloaded")

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
            kwargs: dict[str, Any] = {"text": text, "speed": speed}
            if ref_path and ref_path.exists():
                kwargs["reference_audio"] = str(ref_path)
            if voice_id and voice_id != "default":
                kwargs["voice_id"] = voice_id

            result = self._model.generate(**kwargs)
            audio_array = np.asarray(result.audio, dtype=np.float32)
            sample_rate = getattr(result, "sample_rate", 24000)
            return audio_array, int(sample_rate)
        except Exception as exc:
            logger.error("orpheus.synthesize_failed", error=str(exc))
            raise

    # ------------------------------------------------------------------
    # Voice cloning
    # ------------------------------------------------------------------

    def clone_voice(self, samples: list[Path], name: str = "", language: str = "en") -> dict:
        self._ensure_loaded()
        if not samples:
            raise ValueError("At least one audio sample is required for cloning")

        voice_id = name or f"orpheus_clone_{len(self._cloned_voices)}"
        self._cloned_voices[voice_id] = {
            "voice_id": voice_id,
            "name": name or voice_id,
            "reference": str(samples[0]),
            "language": language,
            "provider": self.name,
        }
        logger.info("orpheus.voice_cloned", voice_id=voice_id)
        return self._cloned_voices[voice_id]

    # ------------------------------------------------------------------
    # Voices & capabilities
    # ------------------------------------------------------------------

    def list_voices(self) -> list[dict]:
        voices: list[dict] = [
            {
                "voice_id": "default",
                "name": "Orpheus Default",
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
            "installed": _ORPHEUS_AVAILABLE,
            "is_loaded": self.is_loaded,
            "supports_cloning": True,
            "supports_zero_shot": True,
            "supports_streaming": False,
            "supports_ssml": False,
            "supports_emotion_tags": True,
            "emotion_tags": self.EMOTION_TAGS,
            "requires_gpu": True,
            "vram_estimate_mb": self.vram_estimate_mb,
            "supported_languages": ["en"],
            "model": "orpheus-tts/orpheus-3b",
        }

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def vram_estimate_mb(self) -> int:
        return 8000

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            raise RuntimeError(
                f"{self.display_name} model is not loaded. Call POST /providers/{self.name}/load first."
            )
