"""Abstract base class for all TTS providers."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class ProviderCapabilities:
    """Declares what a provider supports — UI adapts dynamically."""

    supports_cloning: bool = False
    supports_fine_tuning: bool = False
    supports_streaming: bool = False
    supports_ssml: bool = False
    supports_zero_shot: bool = False
    supports_batch: bool = False
    requires_gpu: bool = False
    gpu_mode: str = "none"  # none, docker_gpu, host_cpu, configurable
    min_samples_for_cloning: int = 0
    max_text_length: int = 5000
    supported_languages: list[str] = field(default_factory=lambda: ["en"])
    supported_output_formats: list[str] = field(default_factory=lambda: ["wav"])


@dataclass
class ProviderHealth:
    """Health check result."""

    name: str
    healthy: bool
    latency_ms: int | None = None
    error: str | None = None


@dataclass
class AudioResult:
    """Result of a synthesis operation."""

    audio_path: Path
    duration_seconds: float | None = None
    sample_rate: int = 22050
    format: str = "wav"


@dataclass
class ProviderAudioSample:
    """An audio sample for training/cloning."""

    file_path: Path
    duration_seconds: float | None = None
    sample_rate: int | None = None


# Backward-compatible alias — prefer ProviderAudioSample in new code.
AudioSample = ProviderAudioSample


@dataclass
class VoiceInfo:
    """Information about an available voice."""

    voice_id: str
    name: str
    language: str = "en"
    gender: str | None = None
    description: str | None = None
    preview_url: str | None = None


@dataclass
class VoiceModel:
    """Result of a training/cloning operation."""

    model_id: str
    model_path: Path | None = None
    provider_model_id: str | None = None
    metrics: dict | None = None


@dataclass
class SynthesisSettings:
    """Settings for synthesis."""

    speed: float = 1.0
    pitch: float = 0.0
    volume: float = 1.0
    output_format: str = "wav"
    ssml: bool = False


@dataclass
class CloneConfig:
    """Configuration for voice cloning."""

    name: str = ""
    description: str = ""
    language: str = "en"


@dataclass
class FineTuneConfig:
    """Configuration for fine-tuning."""

    epochs: int = 10
    learning_rate: float = 1e-5
    batch_size: int = 4


async def run_sync(func, *args, **kwargs):
    """Run a blocking function in a thread executor to avoid blocking the event loop."""
    import asyncio
    from functools import partial

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


class TTSProvider(ABC):
    """Abstract base for all TTS providers."""

    _runtime_config: dict | None = None

    def configure(self, config: dict) -> None:
        """Apply runtime configuration overrides."""
        self._runtime_config = config

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get config value, checking runtime overrides first, then fallback."""
        if hasattr(self, '_runtime_config') and self._runtime_config and key in self._runtime_config:
            return self._runtime_config[key]
        return default

    def prepare_output_path(self, prefix: str = "synth", ext: str = "wav") -> Path:
        """Create the output directory and return a unique file path for synthesis output."""
        output_dir = Path(settings.storage_path) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{prefix}_{uuid.uuid4().hex[:12]}.{ext}"
        logger.debug("output_path_prepared", path=str(output_path))
        return output_path

    @abstractmethod
    async def synthesize(
        self, text: str, voice_id: str, settings: SynthesisSettings
    ) -> AudioResult:
        """Synthesize text to speech."""

    @abstractmethod
    async def clone_voice(
        self, samples: list[ProviderAudioSample], config: CloneConfig
    ) -> VoiceModel:
        """Clone a voice from audio samples (if supported)."""

    @abstractmethod
    async def fine_tune(
        self, model_id: str, samples: list[ProviderAudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        """Fine-tune an existing model (if supported)."""

    @abstractmethod
    async def list_voices(self) -> list[VoiceInfo]:
        """List available voices/models."""

    @abstractmethod
    async def get_capabilities(self) -> ProviderCapabilities:
        """Return provider capability flags for UI adaptation."""

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check if provider is reachable and operational."""

    async def stream_synthesize(
        self, text: str, voice_id: str, settings: SynthesisSettings
    ) -> AsyncIterator[bytes]:
        """Streaming synthesis (optional, raise NotImplementedError if unavailable)."""
        logger.warning(
            "stream_synthesize_not_supported",
            provider=type(self).__name__,
            voice_id=voice_id,
        )
        raise NotImplementedError("Streaming not supported by this provider")
        yield  # Make it an async generator
