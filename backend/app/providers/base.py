"""Abstract base class for all TTS providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path


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
class AudioSample:
    """An audio sample for training/cloning."""

    file_path: Path
    duration_seconds: float | None = None
    sample_rate: int | None = None


@dataclass
class VoiceInfo:
    """Information about an available voice."""

    voice_id: str
    name: str
    language: str = "en"
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

    @abstractmethod
    async def synthesize(
        self, text: str, voice_id: str, settings: SynthesisSettings
    ) -> AudioResult:
        """Synthesize text to speech."""

    @abstractmethod
    async def clone_voice(
        self, samples: list[AudioSample], config: CloneConfig
    ) -> VoiceModel:
        """Clone a voice from audio samples (if supported)."""

    @abstractmethod
    async def fine_tune(
        self, model_id: str, samples: list[AudioSample], config: FineTuneConfig
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
        raise NotImplementedError("Streaming not supported by this provider")
        yield  # Make it an async generator
