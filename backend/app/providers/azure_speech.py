"""Azure AI Speech provider — cloud TTS with SSML support and Custom Neural Voice."""

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


class AzureSpeechProvider(TTSProvider):
    """Azure AI Speech — cloud TTS with SSML and Custom Neural Voice."""

    def __init__(self) -> None:
        self._speech_config = None

    def _get_config(self):
        if self._speech_config is None:
            if not settings.azure_speech_key:
                raise ValueError("AZURE_SPEECH_KEY not configured")
            try:
                import azure.cognitiveservices.speech as speechsdk

                self._speech_config = speechsdk.SpeechConfig(
                    subscription=settings.azure_speech_key,
                    region=settings.azure_speech_region,
                )
                self._speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
                )
                logger.info("azure_speech_config_created", region=settings.azure_speech_region)
            except ImportError:
                raise ImportError("pip install azure-cognitiveservices-speech")
        return self._speech_config

    async def synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AudioResult:
        import azure.cognitiveservices.speech as speechsdk

        config = self._get_config()
        output_dir = Path(settings.storage_path) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"azure_{uuid.uuid4().hex[:12]}.wav"

        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_file))
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=config, audio_config=audio_config
        )

        start = time.perf_counter()

        if settings_.ssml:
            result = await run_sync(synthesizer.speak_ssml_async(text).get)
        else:
            config.speech_synthesis_voice_name = voice_id or "en-US-JennyNeural"
            result = await run_sync(synthesizer.speak_text_async(text).get)

        elapsed = time.perf_counter() - start

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logger.info("azure_synthesis_complete", latency_ms=int(elapsed * 1000))
            return AudioResult(
                audio_path=output_file,
                sample_rate=16000,
                format="wav",
            )
        else:
            error = result.cancellation_details.error_details if result.cancellation_details else "Unknown error"
            raise RuntimeError(f"Azure synthesis failed: {error}")

    async def clone_voice(
        self, samples: list[AudioSample], config: CloneConfig
    ) -> VoiceModel:
        raise NotImplementedError(
            "Azure Custom Neural Voice requires portal setup. "
            "Create your CNV project at speech.microsoft.com"
        )

    async def fine_tune(
        self, model_id: str, samples: list[AudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        raise NotImplementedError("Azure CNV fine-tuning is managed via Azure portal")

    async def list_voices(self) -> list[VoiceInfo]:
        import azure.cognitiveservices.speech as speechsdk

        config = self._get_config()
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=None)
        result = await run_sync(synthesizer.get_voices_async().get)

        voices = []
        for v in result.voices:
            voices.append(VoiceInfo(
                voice_id=v.short_name,
                name=v.local_name,
                language=v.locale,
                description=f"{v.voice_type.name} — {v.gender.name}",
            ))
        return voices

    async def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_cloning=True,
            supports_fine_tuning=False,
            supports_streaming=True,
            supports_ssml=True,
            supports_zero_shot=False,
            supports_batch=True,
            requires_gpu=False,
            gpu_mode="none",
            min_samples_for_cloning=0,
            max_text_length=10000,
            supported_languages=["en", "es", "fr", "de", "it", "pt", "zh", "ja",
                                 "ko", "ar", "ru", "nl", "pl", "sv", "tr", "hi"],
            supported_output_formats=["wav", "mp3", "ogg"],
        )

    async def health_check(self) -> ProviderHealth:
        start = time.perf_counter()
        try:
            self._get_config()
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(name="azure_speech", healthy=True, latency_ms=latency)
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(name="azure_speech", healthy=False, latency_ms=latency, error=str(e))
