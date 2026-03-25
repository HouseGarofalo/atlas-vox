"""CosyVoice provider — multilingual, streaming, zero-shot cloning, GPU/CPU configurable."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
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

COSYVOICE_SPEAKERS = [
    "English Female", "English Male", "Chinese Female", "Chinese Male",
    "Japanese Female", "Korean Female", "Spanish Female", "French Female",
]


class CosyVoiceProvider(TTSProvider):
    """CosyVoice — multilingual TTS with streaming and zero-shot cloning."""

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                import torch
                from cosyvoice.cli.cosyvoice import CosyVoice

                device = "cuda" if (
                    settings.cosyvoice_gpu_mode != "host_cpu"
                    and torch.cuda.is_available()
                ) else "cpu"

                self._model = CosyVoice("pretrained_models/CosyVoice-300M-SFT")
                logger.info("cosyvoice_loaded", device=device)
            except ImportError:
                raise ImportError(
                    "CosyVoice not installed. See https://github.com/FunAudioLLM/CosyVoice"
                )
        return self._model

    async def synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AudioResult:
        model = self._get_model()
        output_dir = Path(settings.storage_path) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"cosyvoice_{uuid.uuid4().hex[:12]}.wav"

        start = time.perf_counter()

        # Use SFT inference for preset speakers (run in executor)
        output = await run_sync(model.inference_sft, text, voice_id or "English Female")

        import torchaudio
        torchaudio.save(str(output_file), output["tts_speech"], 22050)

        elapsed = time.perf_counter() - start
        logger.info("cosyvoice_synthesis_complete", latency_ms=int(elapsed * 1000))

        return AudioResult(audio_path=output_file, sample_rate=22050, format="wav")

    async def clone_voice(
        self, samples: list[AudioSample], config: CloneConfig
    ) -> VoiceModel:
        if not samples:
            raise ValueError("At least one audio sample is required")

        model_id = uuid.uuid4().hex[:12]
        return VoiceModel(
            model_id=model_id,
            model_path=samples[0].file_path,
            provider_model_id=str(samples[0].file_path),
            metrics={"method": "zero_shot", "prompt_audio": str(samples[0].file_path)},
        )

    async def fine_tune(
        self, model_id: str, samples: list[AudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        raise NotImplementedError("CosyVoice fine-tuning not yet supported")

    async def list_voices(self) -> list[VoiceInfo]:
        return [
            VoiceInfo(voice_id=name, name=name, language=name.split()[0].lower()[:2])
            for name in COSYVOICE_SPEAKERS
        ]

    async def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_cloning=True,
            supports_fine_tuning=False,
            supports_streaming=True,
            supports_ssml=False,
            supports_zero_shot=True,
            supports_batch=True,
            requires_gpu=False,
            gpu_mode=settings.cosyvoice_gpu_mode,
            min_samples_for_cloning=1,
            max_text_length=5000,
            supported_languages=["en", "zh", "ja", "ko", "es", "fr", "de", "it", "pt"],
            supported_output_formats=["wav"],
        )

    async def health_check(self) -> ProviderHealth:
        start = time.perf_counter()
        try:
            self._get_model()
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(name="cosyvoice", healthy=True, latency_ms=latency)
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(name="cosyvoice", healthy=False, latency_ms=latency, error=str(e))

    async def stream_synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AsyncIterator[bytes]:
        model = self._get_model()
        import io

        import soundfile as sf

        # CosyVoice streaming via inference_sft generator
        for chunk_output in model.inference_sft(text, voice_id or "English Female", stream=True):
            audio = chunk_output["tts_speech"].numpy()
            buf = io.BytesIO()
            sf.write(buf, audio.squeeze(), 22050, format="WAV")
            yield buf.getvalue()
