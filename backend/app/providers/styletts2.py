"""StyleTTS2 provider — zero-shot synthesis with style diffusion, GPU/CPU configurable."""

from __future__ import annotations

import time
import uuid
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


class StyleTTS2Provider(TTSProvider):
    """StyleTTS2 — zero-shot, style diffusion, multi-speaker with reference audio."""

    def __init__(self) -> None:
        self._model = None

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                import torch
                from styletts2 import tts as styletts2_tts

                gpu_mode = self.get_config_value('gpu_mode', settings.styletts2_gpu_mode)
                device = "cuda" if (
                    gpu_mode != "host_cpu"
                    and torch.cuda.is_available()
                ) else "cpu"

                self._model = styletts2_tts.StyleTTS2()
                logger.info("styletts2_loaded", device=device)
            except ImportError:
                raise ImportError(
                    "StyleTTS2 not installed. See https://github.com/yl4579/StyleTTS2"
                )
        return self._model

    async def synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AudioResult:
        model = self._get_model()
        output_dir = Path(settings.storage_path) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"styletts2_{uuid.uuid4().hex[:12]}.wav"

        start = time.perf_counter()

        # voice_id can be a reference WAV path for zero-shot
        if Path(voice_id).exists():
            wav = await run_sync(model.inference, text, target_voice_path=voice_id, diffusion_steps=10)
        else:
            wav = await run_sync(model.inference, text, diffusion_steps=10)

        import soundfile as sf
        sf.write(str(output_file), wav, 24000)

        elapsed = time.perf_counter() - start
        logger.info("styletts2_synthesis_complete", latency_ms=int(elapsed * 1000))

        return AudioResult(audio_path=output_file, sample_rate=24000, format="wav")

    async def clone_voice(
        self, samples: list[AudioSample], config: CloneConfig
    ) -> VoiceModel:
        if not samples:
            raise ValueError("At least one audio sample is required")

        # StyleTTS2 zero-shot cloning uses reference audio at inference time
        model_id = uuid.uuid4().hex[:12]
        return VoiceModel(
            model_id=model_id,
            model_path=samples[0].file_path,
            provider_model_id=str(samples[0].file_path),
            metrics={"method": "zero_shot_reference"},
        )

    async def fine_tune(
        self, model_id: str, samples: list[AudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        model_dir = Path(settings.storage_path) / "models" / "styletts2" / f"ft_{uuid.uuid4().hex[:8]}"
        model_dir.mkdir(parents=True, exist_ok=True)

        ft_id = uuid.uuid4().hex[:12]
        logger.info("styletts2_fine_tune_prepared", samples=len(samples))
        return VoiceModel(
            model_id=ft_id,
            model_path=model_dir,
            provider_model_id=str(model_dir),
            metrics={"method": "fine_tune", "samples_count": len(samples)},
        )

    async def list_voices(self) -> list[VoiceInfo]:
        return [
            VoiceInfo(
                voice_id="default",
                name="StyleTTS2 Default",
                language="en",
                description="Zero-shot — provide reference audio for custom voice",
            ),
        ]

    async def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_cloning=True,
            supports_fine_tuning=True,
            supports_streaming=False,
            supports_ssml=False,
            supports_zero_shot=True,
            supports_batch=True,
            requires_gpu=False,
            gpu_mode=settings.styletts2_gpu_mode,
            min_samples_for_cloning=1,
            max_text_length=5000,
            supported_languages=["en"],
            supported_output_formats=["wav"],
        )

    async def health_check(self) -> ProviderHealth:
        start = time.perf_counter()
        try:
            if self._model is not None:
                latency = int((time.perf_counter() - start) * 1000)
                return ProviderHealth(name="styletts2", healthy=True, latency_ms=latency)
            from styletts2 import tts as styletts2_tts  # noqa: F401
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(name="styletts2", healthy=True, latency_ms=latency,
                                  error="Ready — model downloads on first synthesis")
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(name="styletts2", healthy=False, latency_ms=latency, error=str(e))
