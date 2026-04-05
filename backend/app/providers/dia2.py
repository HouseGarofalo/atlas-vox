"""Dia2 provider (2B) — streaming dialogue generation, multi-speaker."""

from __future__ import annotations

import io
import time
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
        output_file = self.prepare_output_path(prefix="dia2")

        logger.info("dia2_synthesize_started", voice_id=voice_id, text_length=len(text))
        start = time.perf_counter()

        if "[S1]" not in text and "[S2]" not in text:
            text = f"[S1] {text}"

        try:
            output = await run_sync(model.generate, text)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error("dia2_synthesize_failed", voice_id=voice_id, latency_ms=int(elapsed * 1000), error=str(exc))
            raise

        import soundfile as sf
        sf.write(str(output_file), output, model.sample_rate)

        elapsed = time.perf_counter() - start
        logger.info(
            "dia2_synthesize_completed",
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
        raise NotImplementedError("Dia2 does not support voice cloning directly")

    async def fine_tune(
        self, model_id: str, samples: list[ProviderAudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        raise NotImplementedError("Dia2 does not support fine-tuning")

    async def list_voices(self) -> list[VoiceInfo]:
        voices = [
            VoiceInfo(voice_id="S1", name="Speaker 1 (Dia2)", language="en",
                      description="Primary dialogue speaker"),
            VoiceInfo(voice_id="S2", name="Speaker 2 (Dia2)", language="en",
                      description="Secondary dialogue speaker"),
        ]
        logger.info("dia2_voices_listed", count=len(voices))
        return voices

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
                logger.info("dia2_health_check", healthy=True, latency_ms=0, model_loaded=True)
                return ProviderHealth(name="dia2", healthy=True, latency_ms=0)
            from dia.model import Dia as _Dia  # noqa: F401
            logger.info("dia2_health_check", healthy=True, latency_ms=0, model_loaded=False)
            return ProviderHealth(name="dia2", healthy=True, latency_ms=0)
        except ImportError:
            logger.info("dia2_health_check", healthy=True, latency_ms=0, note="gpu_worker_only")
            return ProviderHealth(name="dia2", healthy=True, latency_ms=0,
                                  error="Available in GPU worker only")
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            logger.info("dia2_health_check", healthy=False, latency_ms=latency, error=str(e))
            return ProviderHealth(name="dia2", healthy=False, latency_ms=latency, error=str(e))

    def _iter_stream_chunks(self, text: str, queue: "asyncio.Queue[bytes | None]", loop: "asyncio.AbstractEventLoop") -> None:
        """Iterate Dia2 streaming chunks in a thread, pushing each to the queue."""
        import soundfile as sf

        model = self._get_model()
        try:
            for chunk in model.generate(text, stream=True):
                buf = io.BytesIO()
                sf.write(buf, chunk, model.sample_rate, format="WAV")
                loop.call_soon_threadsafe(queue.put_nowait, buf.getvalue())
        except Exception as exc:
            logger.error("dia2_stream_chunk_error", error=str(exc))
            raise
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    async def stream_synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AsyncIterator[bytes]:
        """Stream synthesis — yields audio chunks as the model produces them."""
        import asyncio

        if "[S1]" not in text and "[S2]" not in text:
            text = f"[S1] {text}"

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        # Run the blocking chunk generator in a thread; it pushes to the queue
        # as each chunk completes rather than waiting for the full output.
        future = loop.run_in_executor(None, self._iter_stream_chunks, text, queue, loop)
        try:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            # Ensure the executor task is awaited to surface any exceptions.
            await future
