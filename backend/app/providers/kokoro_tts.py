"""Kokoro TTS provider — lightweight, CPU-only, 54 built-in voices."""

from __future__ import annotations

import time
from pathlib import Path

import structlog

from app.core.config import settings
from app.providers.base import (
    AudioResult,
    AudioSample,
    CloneConfig,
    FineTuneConfig,
    ProviderCapabilities,
    ProviderHealth,
    SynthesisSettings,
    TTSProvider,
    VoiceInfo,
    VoiceModel,
    run_sync,
)

logger = structlog.get_logger(__name__)


class KokoroTTSProvider(TTSProvider):
    """Kokoro TTS — 82M params, fast CPU inference, 54 voices."""

    def __init__(self) -> None:
        self._pipeline = None
        self._voices: list[VoiceInfo] | None = None

    def _get_pipeline(self):
        """Lazy-load the Kokoro pipeline."""
        if self._pipeline is None:
            try:
                from kokoro import KPipeline
                self._pipeline = KPipeline(lang_code="a")  # American English
                logger.info("kokoro_pipeline_loaded")
            except ImportError:
                logger.error("kokoro_not_installed", hint="pip install kokoro>=0.9.4")
                raise
        return self._pipeline

    async def synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AudioResult:
        """Generate speech from text using Kokoro."""
        pipeline = self._get_pipeline()
        output_dir = Path(settings.storage_path) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        import uuid
        output_file = output_dir / f"kokoro_{uuid.uuid4().hex[:12]}.wav"

        start = time.perf_counter()

        def _synth():
            gen = pipeline(text, voice=voice_id, speed=settings_.speed)
            import numpy as np
            import soundfile as sf
            chunks = [audio for _gs, _ps, audio in gen]
            if not chunks:
                raise RuntimeError("Kokoro produced no audio output")
            full = np.concatenate(chunks)
            sf.write(str(output_file), full, 24000)
            return full

        full_audio = await run_sync(_synth)
        sample_rate = 24000

        duration = len(full_audio) / sample_rate
        elapsed = time.perf_counter() - start
        logger.info("kokoro_synthesis_complete", duration_s=duration, latency_ms=int(elapsed * 1000))

        return AudioResult(
            audio_path=output_file,
            duration_seconds=duration,
            sample_rate=sample_rate,
            format="wav",
        )

    async def clone_voice(
        self, samples: list[AudioSample], config: CloneConfig
    ) -> VoiceModel:
        """Kokoro does not support voice cloning."""
        raise NotImplementedError("Kokoro does not support voice cloning")

    async def fine_tune(
        self, model_id: str, samples: list[AudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        """Kokoro does not support fine-tuning."""
        raise NotImplementedError("Kokoro does not support fine-tuning")

    async def list_voices(self) -> list[VoiceInfo]:
        """List Kokoro's 54 built-in voices."""
        if self._voices is not None:
            return self._voices

        # Kokoro voice naming: af_heart, af_bella, am_adam, bf_emma, etc.
        # a=American, b=British; f=female, m=male
        default_voices = [
            VoiceInfo(voice_id="af_heart", name="Heart (American Female)", language="en"),
            VoiceInfo(voice_id="af_bella", name="Bella (American Female)", language="en"),
            VoiceInfo(voice_id="af_sarah", name="Sarah (American Female)", language="en"),
            VoiceInfo(voice_id="af_nicole", name="Nicole (American Female)", language="en"),
            VoiceInfo(voice_id="am_adam", name="Adam (American Male)", language="en"),
            VoiceInfo(voice_id="am_michael", name="Michael (American Male)", language="en"),
            VoiceInfo(voice_id="bf_emma", name="Emma (British Female)", language="en"),
            VoiceInfo(voice_id="bm_george", name="George (British Male)", language="en"),
            VoiceInfo(voice_id="bm_lewis", name="Lewis (British Male)", language="en"),
        ]
        self._voices = default_voices
        return self._voices

    async def get_capabilities(self) -> ProviderCapabilities:
        """Kokoro capabilities: CPU-only, no cloning, no streaming."""
        return ProviderCapabilities(
            supports_cloning=False,
            supports_fine_tuning=False,
            supports_streaming=False,
            supports_ssml=False,
            supports_zero_shot=False,
            supports_batch=True,
            requires_gpu=False,
            gpu_mode="none",
            min_samples_for_cloning=0,
            max_text_length=5000,
            supported_languages=["en"],
            supported_output_formats=["wav"],
        )

    async def health_check(self) -> ProviderHealth:
        """Check if Kokoro is installed and usable."""
        start = time.perf_counter()
        try:
            self._get_pipeline()
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(name="kokoro", healthy=True, latency_ms=latency)
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(
                name="kokoro", healthy=False, latency_ms=latency, error=str(e)
            )
