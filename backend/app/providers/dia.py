"""Dia provider (1.6B) — dialogue generation with [S1]/[S2] tags, non-verbal support."""

from __future__ import annotations

import time
import uuid

import structlog

from app.core.config import settings
from app.providers.base import (
    AudioResult,
    CloneConfig,
    FineTuneConfig,
    ProviderAudioSample,
    ProviderCapabilities,
    ProviderHealth,
    SynthesisSettings,
    TTSProvider,
    VoiceInfo,
    VoiceModel,
    run_sync,
)

logger = structlog.get_logger(__name__)


class DiaProvider(TTSProvider):
    """Nari-labs Dia 1.6B — dialogue TTS with [S1]/[S2] tags, non-verbal sounds."""

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

                gpu_mode = self.get_config_value('gpu_mode', settings.dia_gpu_mode)
                device = "cuda" if (
                    gpu_mode != "host_cpu"
                    and torch.cuda.is_available()
                ) else "cpu"

                self._model = Dia.from_pretrained("nari-labs/Dia-1.6B", device=device)
                logger.info("dia_loaded", device=device)
            except ImportError:
                raise ImportError(
                    "Dia not installed. pip install git+https://github.com/nari-labs/dia.git"
                )
        return self._model

    async def synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AudioResult:
        model = self._get_model()
        output_file = self.prepare_output_path(prefix="dia")

        logger.info("dia_synthesize_started", voice_id=voice_id, text_length=len(text))
        start = time.perf_counter()

        # Dia expects dialogue format with [S1]/[S2] tags
        # If no tags present, wrap in [S1]
        if "[S1]" not in text and "[S2]" not in text:
            text = f"[S1] {text}"

        try:
            output = await run_sync(model.generate, text)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error("dia_synthesize_failed", voice_id=voice_id, latency_ms=int(elapsed * 1000), error=str(exc))
            raise

        import soundfile as sf
        sf.write(str(output_file), output, model.sample_rate)

        elapsed = time.perf_counter() - start
        logger.info(
            "dia_synthesize_completed",
            voice_id=voice_id,
            duration_seconds=len(output) / model.sample_rate if hasattr(model, "sample_rate") else None,
            latency_ms=int(elapsed * 1000),
        )

        return AudioResult(
            audio_path=output_file,
            sample_rate=model.sample_rate,
            format="wav",
        )

    async def clone_voice(
        self, samples: list[ProviderAudioSample], config: CloneConfig
    ) -> VoiceModel:
        if not samples:
            raise ValueError("Audio sample required for voice conditioning")

        # Verify the library is present before claiming a voice was conditioned.
        try:
            from dia.model import Dia  # noqa: F401
        except ImportError as exc:
            raise NotImplementedError(
                "Dia is not installed. "
                "Install it with: pip install git+https://github.com/nari-labs/dia.git"
            ) from exc

        # Dia uses audio conditioning with 5-10s reference.
        total_dur = sum(s.duration_seconds or 0 for s in samples)
        if total_dur < 5.0:
            raise ValueError(f"Dia requires 5-10s of reference audio, got {total_dur:.1f}s")

        model_id = uuid.uuid4().hex[:12]
        return VoiceModel(
            model_id=model_id,
            model_path=samples[0].file_path,
            provider_model_id=str(samples[0].file_path),
            metrics={"method": "audio_conditioning", "ref_duration_s": total_dur},
        )

    async def fine_tune(
        self, model_id: str, samples: list[ProviderAudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        raise NotImplementedError("Dia does not support fine-tuning")

    async def list_voices(self) -> list[VoiceInfo]:
        voices = [
            VoiceInfo(voice_id="S1", name="Speaker 1 (Dia)", language="en",
                      description="Primary dialogue speaker"),
            VoiceInfo(voice_id="S2", name="Speaker 2 (Dia)", language="en",
                      description="Secondary dialogue speaker"),
        ]
        logger.info("dia_voices_listed", count=len(voices))
        return voices

    async def get_capabilities(self) -> ProviderCapabilities:
        # Only advertise cloning when the Dia library is actually importable.
        can_clone = False
        try:
            from dia.model import Dia  # noqa: F401
            can_clone = True
        except ImportError:
            pass

        return ProviderCapabilities(
            supports_cloning=can_clone,
            supports_fine_tuning=False,
            supports_streaming=False,
            supports_ssml=False,
            supports_zero_shot=False,
            supports_batch=True,
            requires_gpu=False,
            gpu_mode=settings.dia_gpu_mode,
            min_samples_for_cloning=1,
            max_text_length=5000,
            supported_languages=["en"],
            supported_output_formats=["wav"],
        )

    async def health_check(self) -> ProviderHealth:
        start = time.perf_counter()
        try:
            if self._model is not None:
                logger.info("dia_health_check", healthy=True, latency_ms=0, model_loaded=True)
                return ProviderHealth(name="dia", healthy=True, latency_ms=0)
            from dia.model import Dia as _Dia  # noqa: F401
            logger.info("dia_health_check", healthy=True, latency_ms=0, model_loaded=False)
            return ProviderHealth(name="dia", healthy=True, latency_ms=0)
        except ImportError:
            logger.info("dia_health_check", healthy=True, latency_ms=0, note="gpu_worker_only")
            return ProviderHealth(name="dia", healthy=True, latency_ms=0,
                                  error="Available in GPU worker only")
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            logger.info("dia_health_check", healthy=False, latency_ms=latency, error=str(e))
            return ProviderHealth(name="dia", healthy=False, latency_ms=latency, error=str(e))
