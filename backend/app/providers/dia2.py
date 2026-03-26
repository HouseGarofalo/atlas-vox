"""Dia2 provider (2B) — streaming dialogue generation, multi-speaker."""

from __future__ import annotations

import io
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


class Dia2Provider(TTSProvider):
    """Nari-labs Dia2 2B — streaming dialogue TTS with multi-speaker support."""

    def __init__(self) -> None:
        self._model = None

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                import torch
                from dia.model import Dia

                gpu_mode = self.get_config_value('gpu_mode', settings.dia2_gpu_mode)
                device = "cuda" if (
                    gpu_mode != "host_cpu"
                    and torch.cuda.is_available()
                ) else "cpu"

                self._model = Dia.from_pretrained("nari-labs/Dia2-2B", device=device)
                logger.info("dia2_loaded", device=device)
            except ImportError:
                raise ImportError(
                    "Dia2 not installed. See https://github.com/nari-labs/Dia2"
                )
        return self._model

    async def synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AudioResult:
        model = self._get_model()
        output_dir = Path(settings.storage_path) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"dia2_{uuid.uuid4().hex[:12]}.wav"

        start = time.perf_counter()

        if "[S1]" not in text and "[S2]" not in text:
            text = f"[S1] {text}"

        output = await run_sync(model.generate, text)

        import soundfile as sf
        sf.write(str(output_file), output, model.sample_rate)

        elapsed = time.perf_counter() - start
        logger.info("dia2_synthesis_complete", latency_ms=int(elapsed * 1000))

        return AudioResult(
            audio_path=output_file,
            sample_rate=model.sample_rate,
            format="wav",
        )

    async def clone_voice(
        self, samples: list[AudioSample], config: CloneConfig
    ) -> VoiceModel:
        raise NotImplementedError("Dia2 does not support voice cloning directly")

    async def fine_tune(
        self, model_id: str, samples: list[AudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        raise NotImplementedError("Dia2 does not support fine-tuning")

    async def list_voices(self) -> list[VoiceInfo]:
        return [
            VoiceInfo(voice_id="S1", name="Speaker 1 (Dia2)", language="en",
                      description="Primary dialogue speaker"),
            VoiceInfo(voice_id="S2", name="Speaker 2 (Dia2)", language="en",
                      description="Secondary dialogue speaker"),
        ]

    async def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_cloning=False,
            supports_fine_tuning=False,
            supports_streaming=True,
            supports_ssml=False,
            supports_zero_shot=False,
            supports_batch=True,
            requires_gpu=False,
            gpu_mode=settings.dia2_gpu_mode,
            min_samples_for_cloning=0,
            max_text_length=5000,
            supported_languages=["en"],
            supported_output_formats=["wav"],
        )

    async def health_check(self) -> ProviderHealth:
        start = time.perf_counter()
        try:
            if self._model is not None:
                return ProviderHealth(name="dia2", healthy=True, latency_ms=0)
            from dia.model import Dia as _Dia  # noqa: F401
            return ProviderHealth(name="dia2", healthy=True, latency_ms=0)
        except ImportError:
            return ProviderHealth(name="dia2", healthy=True, latency_ms=0,
                                  error="Available in GPU worker only")
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(name="dia2", healthy=False, latency_ms=latency, error=str(e))

    async def stream_synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AsyncIterator[bytes]:
        model = self._get_model()
        import soundfile as sf

        if "[S1]" not in text and "[S2]" not in text:
            text = f"[S1] {text}"

        for chunk in model.generate(text, stream=True):
            buf = io.BytesIO()
            sf.write(buf, chunk, model.sample_rate, format="WAV")
            yield buf.getvalue()
