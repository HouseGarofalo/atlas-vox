"""Chatterbox (Resemble AI) GPU provider.

Requires ``pip install chatterbox-tts`` or cloning the Resemble AI repo and
running ``pip install -e .`` from the checkout.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import structlog

from app.providers.base import GPUProviderBase

logger = structlog.get_logger(__name__)

try:
    from chatterbox.tts import ChatterboxTTS  # type: ignore[import-untyped]

    _CHATTERBOX_AVAILABLE = True
except ImportError:
    _CHATTERBOX_AVAILABLE = False
    ChatterboxTTS = None  # type: ignore[assignment,misc]


class ChatterboxProvider(GPUProviderBase):
    """Chatterbox TTS — expressive zero-shot voice cloning by Resemble AI."""

    name = "chatterbox"
    display_name = "Chatterbox (Resemble AI)"

    def __init__(self) -> None:
        self._model: Any = None
        self._device: str = "cuda:0"
        self._cloned_voices: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self, device: str = "cuda:0") -> None:
        if not _CHATTERBOX_AVAILABLE:
            raise RuntimeError("chatterbox-tts is not installed. See: https://github.com/resemble-ai/chatterbox")
        self._device = device
        logger.info("chatterbox.loading", device=device)
        try:
            self._model = ChatterboxTTS.from_pretrained(device=device)
            logger.info("chatterbox.loaded", device=device)
        except Exception as exc:
            logger.error("chatterbox.load_failed", error=str(exc))
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
            logger.info("chatterbox.unloaded")

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
            raise ValueError("Chatterbox requires a reference audio prompt for synthesis.")

        try:
            wav = self._model.generate(text, audio_prompt_path=str(ref_path))
            audio_array = wav.cpu().numpy().squeeze()
            sample_rate = self._model.sr if hasattr(self._model, "sr") else 24000
            return np.asarray(audio_array, dtype=np.float32), int(sample_rate)
        except Exception as exc:
            logger.error("chatterbox.synthesize_failed", error=str(exc))
            raise

    # ------------------------------------------------------------------
    # Voice cloning
    # ------------------------------------------------------------------

    def clone_voice(self, samples: list[Path], name: str = "", language: str = "en") -> dict:
        self._ensure_loaded()
        if not samples:
            raise ValueError("At least one audio sample is required for cloning")

        voice_id = name or f"chatterbox_clone_{len(self._cloned_voices)}"
        self._cloned_voices[voice_id] = {
            "voice_id": voice_id,
            "name": name or voice_id,
            "reference": str(samples[0]),
            "language": language,
            "provider": self.name,
        }
        logger.info("chatterbox.voice_cloned", voice_id=voice_id)
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
            "installed": _CHATTERBOX_AVAILABLE,
            "is_loaded": self.is_loaded,
            "supports_cloning": True,
            "supports_zero_shot": True,
            "supports_streaming": False,
            "supports_ssml": False,
            "requires_gpu": True,
            "vram_estimate_mb": self.vram_estimate_mb,
            "supported_languages": ["en"],
            "model": "resemble-ai/chatterbox",
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
