"""CosyVoice provider — multilingual, streaming, zero-shot cloning, GPU/CPU configurable."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator

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

COSYVOICE_SPEAKERS = [
    # CosyVoice-300M-SFT preset speakers (original Chinese names)
    # The model uses Chinese speaker names internally.
    # English aliases are provided for convenience.
    {"id": "英文女", "name": "English Female", "lang": "en", "gender": "Female"},
    {"id": "英文男", "name": "English Male", "lang": "en", "gender": "Male"},
    {"id": "中文女", "name": "Chinese Female", "lang": "zh", "gender": "Female"},
    {"id": "中文男", "name": "Chinese Male", "lang": "zh", "gender": "Male"},
    {"id": "日语男", "name": "Japanese Male", "lang": "ja", "gender": "Male"},
    {"id": "粤语女", "name": "Cantonese Female", "lang": "zh", "gender": "Female"},
    {"id": "韩语女", "name": "Korean Female", "lang": "ko", "gender": "Female"},
]


class CosyVoiceProvider(TTSProvider):
    """CosyVoice — multilingual TTS with streaming and zero-shot cloning."""

    def __init__(self) -> None:
        self._model = None

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                import torch
                from cosyvoice.cli.cosyvoice import CosyVoice

                gpu_mode = self.get_config_value('gpu_mode', settings.cosyvoice_gpu_mode)
                device = "cuda" if (
                    gpu_mode != "host_cpu"
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
        output_file = self.prepare_output_path(prefix="cosyvoice")

        logger.info("cosyvoice_synthesize_started", voice_id=voice_id, text_length=len(text))
        start = time.perf_counter()

        # Use SFT inference for preset speakers (run in executor)
        # Default to English Female (英文女) if no voice_id provided
        try:
            output = await run_sync(model.inference_sft, text, voice_id or "英文女")
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error("cosyvoice_synthesize_failed", voice_id=voice_id, latency_ms=int(elapsed * 1000), error=str(exc))
            raise

        import torchaudio
        torchaudio.save(str(output_file), output["tts_speech"], 22050)

        elapsed = time.perf_counter() - start
        logger.info(
            "cosyvoice_synthesize_completed",
            voice_id=voice_id,
            latency_ms=int(elapsed * 1000),
        )

        return AudioResult(audio_path=output_file, sample_rate=22050, format="wav")

    async def clone_voice(
        self, samples: list[ProviderAudioSample], config: CloneConfig
    ) -> VoiceModel:
        if not samples:
            raise ValueError("At least one audio sample is required")

        # Ensure the library is available before claiming a clone was registered.
        try:
            from cosyvoice.cli.cosyvoice import CosyVoice  # noqa: F401
        except ImportError as exc:
            raise NotImplementedError(
                "CosyVoice is not installed. "
                "See https://github.com/FunAudioLLM/CosyVoice for installation instructions."
            ) from exc

        model_id = uuid.uuid4().hex[:12]
        return VoiceModel(
            model_id=model_id,
            model_path=samples[0].file_path,
            provider_model_id=str(samples[0].file_path),
            metrics={"method": "zero_shot", "prompt_audio": str(samples[0].file_path)},
        )

    async def fine_tune(
        self, model_id: str, samples: list[ProviderAudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        raise NotImplementedError("CosyVoice fine-tuning not yet supported")

    async def list_voices(self) -> list[VoiceInfo]:
        voices = [
            VoiceInfo(
                voice_id=s["id"],
                name=s["name"],
                language=s["lang"],
                gender=s.get("gender"),
                description=f"CosyVoice SFT preset — {s['name']}",
            )
            for s in COSYVOICE_SPEAKERS
        ]
        logger.info("cosyvoice_voices_listed", count=len(voices))
        return voices

    async def get_capabilities(self) -> ProviderCapabilities:
        # CosyVoice is not pip-installable in the standard backend image.
        # Only claim cloning support if the library is actually importable.
        can_clone = False
        try:
            from cosyvoice.cli.cosyvoice import CosyVoice  # noqa: F401
            can_clone = True
        except ImportError:
            pass

        return ProviderCapabilities(
            supports_cloning=can_clone,
            supports_fine_tuning=False,
            supports_streaming=True,
            supports_ssml=False,
            supports_zero_shot=can_clone,
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
            if self._model is not None:
                logger.info("cosyvoice_health_check", healthy=True, latency_ms=0, model_loaded=True)
                return ProviderHealth(name="cosyvoice", healthy=True, latency_ms=0)
            from cosyvoice.cli.cosyvoice import CosyVoice as _CV  # noqa: F401
            logger.info("cosyvoice_health_check", healthy=True, latency_ms=0, model_loaded=False)
            return ProviderHealth(name="cosyvoice", healthy=True, latency_ms=0)
        except ImportError:
            logger.info("cosyvoice_health_check", healthy=True, latency_ms=0, note="gpu_worker_only")
            return ProviderHealth(name="cosyvoice", healthy=True, latency_ms=0,
                                  error="Available in GPU worker only")
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            logger.info("cosyvoice_health_check", healthy=False, latency_ms=latency, error=str(e))
            return ProviderHealth(name="cosyvoice", healthy=False, latency_ms=latency, error=str(e))

    def _iter_stream_chunks(
        self,
        text: str,
        voice_id: str,
        queue: "asyncio.Queue[bytes | None]",
        loop: "asyncio.AbstractEventLoop",
    ) -> None:
        """Iterate CosyVoice streaming chunks in a thread, pushing each to the queue."""
        import io

        import soundfile as sf

        model = self._get_model()
        try:
            for chunk_output in model.inference_sft(text, voice_id or "英文女", stream=True):
                audio = chunk_output["tts_speech"].numpy()
                buf = io.BytesIO()
                sf.write(buf, audio.squeeze(), 22050, format="WAV")
                loop.call_soon_threadsafe(queue.put_nowait, buf.getvalue())
        except Exception as exc:
            logger.error("cosyvoice_stream_chunk_error", error=str(exc))
            raise
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    async def stream_synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AsyncIterator[bytes]:
        """Stream synthesis — yields audio chunks as the model produces them."""
        import asyncio

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        future = loop.run_in_executor(
            None, self._iter_stream_chunks, text, voice_id, queue, loop
        )
        try:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            await future
