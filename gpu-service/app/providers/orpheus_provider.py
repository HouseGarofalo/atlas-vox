"""Orpheus TTS provider.

Uses the ``orpheus-tts`` WebSocket client SDK to stream speech from a remote
Orpheus inference server.  Local GPU inference requires ``orpheus-speech`` +
vLLM on Linux — on Windows we use the client API only.

Install: ``pip install orpheus-tts``

Required environment variables:
    ORPHEUS_API_KEY  — API key for the Orpheus service (optional during demo)
    ORPHEUS_PROVIDER — Provider name for voice endpoint resolution (e.g. "fireworks")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import structlog

from app.providers.base import GPUProviderBase

logger = structlog.get_logger(__name__)

try:
    from orpheus_tts import OrpheusClient  # type: ignore[import-untyped]

    _ORPHEUS_AVAILABLE = True
except ImportError:
    _ORPHEUS_AVAILABLE = False
    OrpheusClient = None  # type: ignore[assignment,misc]


class OrpheusProvider(GPUProviderBase):
    """Orpheus TTS — Llama-3B based expressive speech synthesis with emotion tags.

    Uses the remote Orpheus API via WebSocket streaming.  Audio is returned as
    PCM int16 at 48 kHz mono and converted to float32 for the common interface.
    """

    name = "orpheus"
    display_name = "Orpheus TTS"

    EMOTION_TAGS = ["<laugh>", "<sigh>", "<gasp>", "<cough>", "<clears_throat>", "<singing>", "<whisper>"]
    SAMPLE_RATE = 48000  # Orpheus outputs 48 kHz PCM

    def __init__(self) -> None:
        self._client: Any = None
        self._device: str = "cpu"  # Client-based — no local GPU required
        self._cloned_voices: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self, device: str = "cuda:0") -> None:
        if not _ORPHEUS_AVAILABLE:
            raise RuntimeError("orpheus-tts is not installed. Run: pip install orpheus-tts")

        self._device = device
        api_key = os.environ.get("ORPHEUS_API_KEY")
        provider = os.environ.get("ORPHEUS_PROVIDER")

        logger.info("orpheus.loading", provider=provider)
        try:
            self._client = OrpheusClient(
                api_key=api_key,
                provider=provider or "fireworks",
            )
            self._client.connect()
            logger.info("orpheus.loaded", provider=provider)
        except Exception as exc:
            logger.error("orpheus.load_failed", error=str(exc))
            self._client = None
            raise

    def unload(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
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

        voice = voice_id if voice_id and voice_id != "default" else "josh"

        try:
            pcm_bytes = self._client.stream_to_bytes(text=text, voice=voice)
            # Orpheus returns PCM int16 at 48 kHz mono
            audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            return audio_float32, self.SAMPLE_RATE
        except Exception as exc:
            logger.error("orpheus.synthesize_failed", error=str(exc))
            raise

    # ------------------------------------------------------------------
    # Voice cloning
    # ------------------------------------------------------------------

    def clone_voice(self, samples: list[Path], name: str = "", language: str = "en") -> dict:
        raise NotImplementedError(
            "Orpheus TTS does not support voice cloning via the client API. "
            "Use Fish Speech or Chatterbox for voice cloning."
        )

    # ------------------------------------------------------------------
    # Voices & capabilities
    # ------------------------------------------------------------------

    def list_voices(self) -> list[dict]:
        voices: list[dict] = [
            {"voice_id": "josh", "name": "Josh", "language": "en", "provider": self.name},
            {"voice_id": "emma", "name": "Emma", "language": "en", "provider": self.name},
            {"voice_id": "default", "name": "Default (Josh)", "language": "en", "provider": self.name},
        ]
        return voices

    def get_capabilities(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "installed": _ORPHEUS_AVAILABLE,
            "is_loaded": self.is_loaded,
            "supports_cloning": False,
            "supports_zero_shot": False,
            "supports_streaming": True,
            "supports_ssml": False,
            "supports_emotion_tags": True,
            "emotion_tags": self.EMOTION_TAGS,
            "requires_gpu": False,
            "requires_api_key": True,
            "vram_estimate_mb": self.vram_estimate_mb,
            "supported_languages": ["en"],
            "model": "canopylabs/orpheus-3b-0.1-ft",
            "notes": "Remote API via WebSocket. Local inference requires Linux + vLLM.",
        }

    @property
    def is_loaded(self) -> bool:
        return self._client is not None

    @property
    def vram_estimate_mb(self) -> int:
        return 0  # Remote API — no local VRAM usage

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            raise RuntimeError(
                f"{self.display_name} is not connected. Call POST /providers/{self.name}/load first."
            )
