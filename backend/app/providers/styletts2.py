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

                # Patch torch.load for PyTorch 2.6+ compatibility
                _orig = torch.load
                def _safe(*a, **kw):
                    kw.setdefault("weights_only", False)
                    return _orig(*a, **kw)
                torch.load = _safe

                # Try local model path first
                local_model = Path(settings.storage_path) / "models" / "styletts2"
                ckpt = local_model / "epochs_2nd_00020.pth"
                cfg = local_model / "config.yml"
                if ckpt.exists() and cfg.exists():
                    self._model = styletts2_tts.StyleTTS2(
                        model_checkpoint_path=str(ckpt),
                        config_path=str(cfg),
                    )
                    logger.info("styletts2_loaded_local", model_dir=str(local_model))
                else:
                    self._model = styletts2_tts.StyleTTS2()
                    logger.info("styletts2_loaded")

                torch.load = _orig
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

        # Verify the library is present before claiming a clone was created.
        try:
            from styletts2 import tts as _styletts2_tts  # noqa: F401
        except ImportError as exc:
            raise NotImplementedError(
                "StyleTTS2 is not installed. "
                "Install it following https://github.com/yl4579/StyleTTS2 "
                "and ensure model weights are downloaded before cloning."
            ) from exc

        # StyleTTS2 zero-shot cloning uses reference audio at inference time.
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
        raise NotImplementedError(
            "StyleTTS2 fine-tuning is not supported via this provider. "
            "See https://github.com/yl4579/StyleTTS2 for the upstream training scripts."
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
        # StyleTTS2 zero-shot cloning requires both the library AND a downloaded model.
        # Without both in place the "clone" silently produces default-voice audio, which
        # is misleading.  Report can_clone=False unless the library is importable; even
        # then the caller is responsible for ensuring the model weights are present.
        # Fine-tuning is not supported via this provider at all.
        can_clone = False
        try:
            from styletts2 import tts as _styletts2_tts  # noqa: F401
            if self._model is not None:
                can_clone = True
            else:
                # Check if model weights exist locally
                import os
                local_ckpt = os.path.join(settings.storage_path, "models", "styletts2", "epochs_2nd_00020.pth")
                if os.path.exists(local_ckpt):
                    can_clone = True
        except ImportError:
            pass

        return ProviderCapabilities(
            supports_cloning=can_clone,
            supports_fine_tuning=False,
            supports_streaming=False,
            supports_ssml=False,
            supports_zero_shot=can_clone,
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
