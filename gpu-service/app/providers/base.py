"""Abstract base class for GPU TTS providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class GPUProviderBase(ABC):
    """Base class for GPU TTS providers.

    Every concrete provider **must** implement all abstract methods.  Providers
    that are not installed should still be importable — they just report
    ``is_loaded = False`` and ``installed = False`` in their capabilities.
    """

    name: str
    display_name: str

    @abstractmethod
    def load(self, device: str = "cuda:0") -> None:
        """Load model weights into GPU VRAM on *device*."""
        ...

    @abstractmethod
    def unload(self) -> None:
        """Release model weights and free VRAM."""
        ...

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        reference_audio: Path | None = None,
    ) -> tuple[np.ndarray, int]:
        """Synthesize *text* and return ``(audio_array, sample_rate)``."""
        ...

    @abstractmethod
    def clone_voice(
        self,
        samples: list[Path],
        name: str = "",
        language: str = "en",
    ) -> dict:
        """Clone a voice from *samples* and return metadata about the new voice."""
        ...

    @abstractmethod
    def list_voices(self) -> list[dict]:
        """Return available voices (built-in + cloned)."""
        ...

    @abstractmethod
    def get_capabilities(self) -> dict:
        """Return a capabilities dictionary describing this provider."""
        ...

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Whether the model is currently loaded in VRAM."""
        ...

    @property
    @abstractmethod
    def vram_estimate_mb(self) -> int:
        """Estimated VRAM usage in megabytes when the model is loaded."""
        ...
