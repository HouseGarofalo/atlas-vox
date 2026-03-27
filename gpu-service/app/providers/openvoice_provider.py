"""OpenVoice v2 GPU provider.

Requires ``pip install -e .`` from the OpenVoice repository checkout.
OpenVoice performs instant voice tone cloning from short reference audio.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import structlog

from app.providers.base import GPUProviderBase

logger = structlog.get_logger(__name__)

try:
    from openvoice import se_extractor  # type: ignore[import-untyped]  # noqa: F401
    from openvoice.api import ToneColorConverter  # type: ignore[import-untyped]  # noqa: F401

    _OPENVOICE_AVAILABLE = True
except ImportError:
    _OPENVOICE_AVAILABLE = False


class OpenVoiceProvider(GPUProviderBase):
    """OpenVoice v2 — instant voice tone cloning."""

    name = "openvoice_v2"
    display_name = "OpenVoice v2"

    def __init__(self) -> None:
        self._tone_converter: Any = None
        self._base_model: Any = None
        self._device: str = "cuda:0"
        self._cloned_voices: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self, device: str = "cuda:0") -> None:
        if not _OPENVOICE_AVAILABLE:
            raise RuntimeError("openvoice is not installed. Clone the repo and run: pip install -e .")
        self._device = device
        logger.info("openvoice.loading", device=device)
        try:
            from openvoice.api import BaseSpeakerTTS, ToneColorConverter  # type: ignore[import-untyped]

            # OpenVoice v2 uses a base speaker model + tone color converter.
            self._base_model = BaseSpeakerTTS(device=device)
            self._tone_converter = ToneColorConverter(device=device)
            logger.info("openvoice.loaded", device=device)
        except Exception as exc:
            logger.error("openvoice.load_failed", error=str(exc))
            self._tone_converter = None
            self._base_model = None
            raise

    def unload(self) -> None:
        self._tone_converter = None
        self._base_model = None
        try:
            import torch

            torch.cuda.empty_cache()
        except Exception:
            pass
        logger.info("openvoice.unloaded")

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
            import soundfile as sf
            import tempfile

            # Step 1: Generate base speech with the base model.
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                base_path = tmp.name
            self._base_model.tts(text, base_path, speed=speed)

            # Step 2: If reference audio provided, apply tone color conversion.
            if ref_path and ref_path.exists():
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    output_path = tmp.name
                self._tone_converter.convert(
                    audio_src_path=base_path,
                    src_se=None,
                    tgt_se=None,
                    output_path=output_path,
                    reference_audio=str(ref_path),
                )
                audio_array, sr = sf.read(output_path)
            else:
                audio_array, sr = sf.read(base_path)

            return np.asarray(audio_array, dtype=np.float32), int(sr)
        except Exception as exc:
            logger.error("openvoice.synthesize_failed", error=str(exc))
            raise

    # ------------------------------------------------------------------
    # Voice cloning
    # ------------------------------------------------------------------

    def clone_voice(self, samples: list[Path], name: str = "", language: str = "en") -> dict:
        self._ensure_loaded()
        if not samples:
            raise ValueError("At least one audio sample is required for cloning")

        voice_id = name or f"openvoice_clone_{len(self._cloned_voices)}"
        self._cloned_voices[voice_id] = {
            "voice_id": voice_id,
            "name": name or voice_id,
            "reference": str(samples[0]),
            "language": language,
            "provider": self.name,
        }
        logger.info("openvoice.voice_cloned", voice_id=voice_id)
        return self._cloned_voices[voice_id]

    # ------------------------------------------------------------------
    # Voices & capabilities
    # ------------------------------------------------------------------

    def list_voices(self) -> list[dict]:
        voices: list[dict] = [
            {
                "voice_id": "default",
                "name": "OpenVoice Default",
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
            "installed": _OPENVOICE_AVAILABLE,
            "is_loaded": self.is_loaded,
            "supports_cloning": True,
            "supports_zero_shot": True,
            "supports_streaming": False,
            "supports_ssml": False,
            "requires_gpu": True,
            "vram_estimate_mb": self.vram_estimate_mb,
            "supported_languages": ["en", "zh", "ja", "ko", "fr", "de", "es", "it", "pt"],
            "model": "myshell-ai/OpenVoiceV2",
        }

    @property
    def is_loaded(self) -> bool:
        return self._tone_converter is not None and self._base_model is not None

    @property
    def vram_estimate_mb(self) -> int:
        return 2000

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            raise RuntimeError(
                f"{self.display_name} model is not loaded. Call POST /providers/{self.name}/load first."
            )
