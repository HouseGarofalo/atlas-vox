"""ElevenLabs provider — cloud API with voice cloning and streaming."""

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


class ElevenLabsProvider(TTSProvider):
    """ElevenLabs — cloud TTS with voice cloning via official SDK."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not settings.elevenlabs_api_key:
                raise ValueError("ELEVENLABS_API_KEY not configured")
            try:
                from elevenlabs.client import ElevenLabs

                self._client = ElevenLabs(api_key=settings.elevenlabs_api_key)
                logger.info("elevenlabs_client_created")
            except ImportError:
                raise ImportError("pip install elevenlabs")
        return self._client

    async def synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AudioResult:
        client = self._get_client()
        output_dir = Path(settings.storage_path) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"elevenlabs_{uuid.uuid4().hex[:12]}.mp3"

        start = time.perf_counter()

        def _synth():
            gen = client.text_to_speech.convert(
                voice_id=voice_id, text=text,
                model_id=settings.elevenlabs_model_id,
                output_format="mp3_44100_128",
            )
            return b"".join(chunk for chunk in gen)

        audio_bytes = await run_sync(_synth)
        output_file.write_bytes(audio_bytes)

        elapsed = time.perf_counter() - start
        logger.info("elevenlabs_synthesis_complete", latency_ms=int(elapsed * 1000))

        return AudioResult(
            audio_path=output_file,
            sample_rate=44100,
            format="mp3",
        )

    async def clone_voice(
        self, samples: list[AudioSample], config: CloneConfig
    ) -> VoiceModel:
        client = self._get_client()

        import contextlib

        def _clone():
            with contextlib.ExitStack() as stack:
                files = [stack.enter_context(open(s.file_path, "rb")) for s in samples]
                return client.clone(
                    name=config.name or f"clone_{uuid.uuid4().hex[:8]}",
                    description=config.description,
                    files=files,
                )

        voice = await run_sync(_clone)

        logger.info("elevenlabs_voice_cloned", voice_id=voice.voice_id)
        return VoiceModel(
            model_id=voice.voice_id,
            provider_model_id=voice.voice_id,
            metrics={"method": "instant_voice_clone"},
        )

    async def fine_tune(
        self, model_id: str, samples: list[AudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        raise NotImplementedError("ElevenLabs fine-tuning is managed via their web dashboard")

    async def list_voices(self) -> list[VoiceInfo]:
        client = self._get_client()
        response = await run_sync(client.voices.get_all)
        return [
            VoiceInfo(
                voice_id=v.voice_id,
                name=v.name,
                language="en",
                description=v.description or "",
                preview_url=v.preview_url,
            )
            for v in response.voices
        ]

    async def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_cloning=True,
            supports_fine_tuning=False,
            supports_streaming=True,
            supports_ssml=False,
            supports_zero_shot=False,
            supports_batch=True,
            requires_gpu=False,
            gpu_mode="none",
            min_samples_for_cloning=1,
            max_text_length=5000,
            supported_languages=["en", "es", "fr", "de", "it", "pt", "pl", "hi",
                                 "ar", "zh", "ja", "ko", "nl", "ru", "sv", "tr"],
            supported_output_formats=["mp3", "wav"],
        )

    async def health_check(self) -> ProviderHealth:
        start = time.perf_counter()
        try:
            client = self._get_client()
            await run_sync(client.voices.get_all)
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(name="elevenlabs", healthy=True, latency_ms=latency)
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(name="elevenlabs", healthy=False, latency_ms=latency, error=str(e))

    async def stream_synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AsyncIterator[bytes]:
        client = self._get_client()

        def _gen():
            return list(client.text_to_speech.convert(
                voice_id=voice_id, text=text,
                model_id=settings.elevenlabs_model_id,
                output_format="mp3_44100_128",
            ))

        chunks = await run_sync(_gen)
        for chunk in chunks:
            yield chunk
