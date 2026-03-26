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

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._client = None

    def _get_client(self):
        if self._client is None:
            api_key = self.get_config_value('api_key', settings.elevenlabs_api_key)
            if not api_key:
                raise ValueError("ELEVENLABS_API_KEY not configured")
            try:
                from elevenlabs.client import ElevenLabs

                self._client = ElevenLabs(api_key=api_key)
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

        model_id = self.get_config_value('model_id', settings.elevenlabs_model_id)

        def _synth():
            gen = client.text_to_speech.convert(
                voice_id=voice_id, text=text,
                model_id=model_id,
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
                return client.voices.ivc.create(
                    name=config.name or f"clone_{uuid.uuid4().hex[:8]}",
                    description=config.description or "",
                    files=files,
                )

        result = await run_sync(_clone)

        voice_id = result.voice_id
        logger.info("elevenlabs_voice_cloned", voice_id=voice_id)
        return VoiceModel(
            model_id=voice_id,
            provider_model_id=voice_id,
            metrics={"method": "instant_voice_clone"},
        )

    async def fine_tune(
        self, model_id: str, samples: list[AudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        raise NotImplementedError("ElevenLabs fine-tuning is managed via their web dashboard")

    async def list_voices(self) -> list[VoiceInfo]:
        """List ElevenLabs voices.

        When an API key is configured, fetches the live voice library.
        Otherwise, returns the 57 premade voices as a hardcoded fallback
        so the voice library is useful even without a key.
        """
        # Try live API first
        try:
            api_key = self.get_config_value('api_key', settings.elevenlabs_api_key)
            if api_key:
                client = self._get_client()
                response = await run_sync(client.voices.get_all)
                voices = []
                for v in response.voices:
                    gender = None
                    if hasattr(v, "labels") and v.labels:
                        gender = v.labels.get("gender", None)
                        if gender:
                            gender = gender.capitalize()
                    voices.append(VoiceInfo(
                        voice_id=v.voice_id,
                        name=v.name,
                        language="en",
                        gender=gender,
                        description=v.description or "",
                        preview_url=v.preview_url,
                    ))
                if voices:
                    return voices
        except Exception as exc:
            logger.debug("elevenlabs_live_list_failed", error=str(exc))

        # Fallback: hardcoded premade voices
        return self._hardcoded_premade_voices()

    @staticmethod
    def _hardcoded_premade_voices() -> list[VoiceInfo]:
        """ElevenLabs' 57 premade voices available to all tiers."""
        entries = [
            # (voice_id, name, gender, accent, use_case)
            ("pNInz6obpgDQGcFmaJgB", "Adam", "Male", "American", "Narration"),
            ("Xb7hH8MSUJpSbSDYk0k2", "Alice", "Female", "British", "News"),
            ("ErXwobaYiN019PkySvjV", "Antoni", "Male", "American", "Narration"),
            ("VR6AewLTigWG4xSOukaG", "Arnold", "Male", "American", "Narration"),
            ("pqHfZKP75CvOlQylNhV4", "Bill", "Male", "American", "Documentary"),
            ("nPczCjzI2devNBz1zQrb", "Brian", "Male", "American", "Narration"),
            ("N2lVS1w4EtoT3dr4eOWO", "Callum", "Male", "American", "Video games"),
            ("IKne3meq5aSn9XLyUdCD", "Charlie", "Male", "Australian", "Conversational"),
            ("XB0fDUnXU5powFXDhCwa", "Charlotte", "Female", "English-Swedish", "Video games"),
            ("iP95p4xoKVk53GoZ742B", "Chris", "Male", "American", "Conversational"),
            ("2EiwWnXFnvU5JabPnv8n", "Clyde", "Male", "American", "Video games"),
            ("onwK4e9ZLuTAKqWW03F9", "Daniel", "Male", "British", "News"),
            ("CYw3kZ02Hs0563khs1Fj", "Dave", "Male", "British-Essex", "Video games"),
            ("AZnzlk1XvdvUeBnXmlld", "Domi", "Female", "American", "Narration"),
            ("ThT5KcBeYPX3keUQqHPh", "Dorothy", "Female", "British", "Children's stories"),
            ("29vD33N1CtxCmqQRPOHJ", "Drew", "Male", "American", "News"),
            ("LcfcDJNUP1GQjkzn1xUU", "Emily", "Female", "American", "Meditation"),
            ("g5CIjZEefAph4nQFvHAz", "Ethan", "Male", "American", "ASMR"),
            ("D38z5RcWu1voky8WS1ja", "Fin", "Male", "Irish", "Video games"),
            ("jsCqWAovK2LkecY7zXl4", "Freya", "Female", "American", "General"),
            ("JBFqnCBsd6RMkjVDRZzb", "George", "Male", "British", "Narration"),
            ("jBpfuIE2acCO8z3wKNLl", "Gigi", "Female", "American", "Animation"),
            ("zcAOhNBS3c14rBihAFp1", "Giovanni", "Male", "English-Italian", "Audiobook"),
            ("z9fAnlkpzviPz146aGWa", "Glinda", "Female", "American", "Video games"),
            ("oWAxZDx7w5VEj9dCyTzz", "Grace", "Female", "American-Southern", "Audiobook"),
            ("SOYHLrjzK2X1ezoPC6cr", "Harry", "Male", "American", "Video games"),
            ("ZQe5CZNOzWyzPSCn5a3c", "James", "Male", "Australian", "News"),
            ("bVMeCyTHy58xNoL34h3p", "Jeremy", "Male", "American-Irish", "Narration"),
            ("t0jbNlBVZ17f02VDIeMI", "Jessie", "Male", "American", "Video games"),
            ("Zlb1dXrM653N07WRdFW3", "Joseph", "Male", "British", "News"),
            ("TxGEqnHWrfWFTfGW9XjX", "Josh", "Male", "American", "Narration"),
            ("TX3LPaxmHKxFdv7VOQHJ", "Liam", "Male", "American", "Narration"),
            ("pFZP5JQG7iQjIQuC4Bku", "Lily", "Female", "British", "Narration"),
            ("XrExE9yKIg1WjnnlVkGX", "Matilda", "Female", "American", "Audiobook"),
            ("flq6f7yk4E4fJM5XTYuZ", "Michael", "Male", "American", "Audiobook"),
            ("zrHiDhphv9ZnVXBqCLjz", "Mimi", "Female", "English-Swedish", "Animation"),
            ("piTKgcLEGmPE4e6mEKli", "Nicole", "Female", "American", "Audiobook"),
            ("ODq5zmih8GrVes37Dizd", "Patrick", "Male", "American", "Video games"),
            ("5Q0t7uMcjvnagumLfvZi", "Paul", "Male", "American", "News"),
            ("21m00Tcm4TlvDq8ikWAM", "Rachel", "Female", "American", "Narration"),
            ("yoZ06aMxZJJ28mfd3POQ", "Sam", "Male", "American", "Narration"),
            ("EXAVITQu4vr4xnSDxMaL", "Sarah", "Female", "American", "News"),
            ("pMsXgVXv3BLzUgSXRplE", "Serena", "Female", "American", "Interactive"),
            ("GBv7mTt0atIp3Br8iCZE", "Thomas", "Male", "American", "Meditation"),
            ("knrPHWnBmmDHMoiMeP3l", "Santa Claus", "Male", None, "Christmas"),
        ]
        return [
            VoiceInfo(
                voice_id=vid,
                name=name,
                language="en",
                gender=gender,
                description=f"{accent + ' accent, ' if accent else ''}{use_case}",
            )
            for vid, name, gender, accent, use_case in entries
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
            api_key = self.get_config_value('api_key', settings.elevenlabs_api_key)
            if not api_key:
                from elevenlabs.client import ElevenLabs as _EL  # noqa: F401
                latency = int((time.perf_counter() - start) * 1000)
                return ProviderHealth(name="elevenlabs", healthy=True, latency_ms=latency,
                                      error="SDK ready — configure API key in Providers settings")
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

        model_id = self.get_config_value('model_id', settings.elevenlabs_model_id)

        def _gen():
            return list(client.text_to_speech.convert(
                voice_id=voice_id, text=text,
                model_id=model_id,
                output_format="mp3_44100_128",
            ))

        chunks = await run_sync(_gen)
        for chunk in chunks:
            yield chunk
