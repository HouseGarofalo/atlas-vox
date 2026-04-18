"""ElevenLabs provider — cloud API with voice cloning, streaming, and advanced features."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

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
    WordBoundary,
    run_sync,
)

logger = structlog.get_logger(__name__)

# Module-level cache for premade voices loaded from JSON
_premade_voices_cache: list[VoiceInfo] | None = None


class ElevenLabsProvider(TTSProvider):
    """ElevenLabs — cloud TTS with voice cloning via official SDK.

    Supports:
    - Text-to-speech synthesis with voice settings (stability, similarity_boost,
      style, speaker boost)
    - Streaming synthesis
    - Synthesis with character-level word boundary timestamps
    - Instant voice cloning (IVC) with optional background noise removal
    - Speech-to-speech voice conversion
    - Voice design from text description
    - Sound effects generation
    - Audio isolation (background noise removal)
    - Multiple model selection (flash, turbo, multilingual)
    """

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

    def _build_voice_settings(self, request_settings: SynthesisSettings | None = None):
        """Build VoiceSettings preferring per-request overrides over shared config.

        When ``request_settings.voice_settings`` supplies ``stability`` /
        ``similarity_boost`` / ``style`` / ``use_speaker_boost`` it wins over
        the shared ``_runtime_config`` — so concurrent syntheses with
        different tunables don't race.
        """
        try:
            from elevenlabs import VoiceSettings
        except ImportError:
            raise ImportError("pip install elevenlabs")

        return VoiceSettings(
            stability=float(self.resolve_setting('stability', request_settings, 0.5)),
            similarity_boost=float(self.resolve_setting('similarity_boost', request_settings, 0.75)),
            style=float(self.resolve_setting('style', request_settings, 0.0)),
            use_speaker_boost=bool(self.resolve_setting('use_speaker_boost', request_settings, False)),
        )

    def _get_model_id(self, request_settings: SynthesisSettings | None = None) -> str:
        return self.resolve_setting('model_id', request_settings, settings.elevenlabs_model_id)

    async def synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AudioResult:
        client = self._get_client()
        output_file = self.prepare_output_path(prefix="elevenlabs", ext="mp3")

        logger.info("elevenlabs_synthesize_started", voice_id=voice_id, text_length=len(text))
        start = time.perf_counter()

        model_id = self._get_model_id(settings_)
        voice_settings = self._build_voice_settings(settings_)

        def _synth():
            gen = client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=model_id,
                output_format="mp3_44100_128",
                voice_settings=voice_settings,
            )
            return b"".join(chunk for chunk in gen)

        try:
            audio_bytes = await run_sync(_synth)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error(
                "elevenlabs_synthesize_failed",
                voice_id=voice_id,
                latency_ms=int(elapsed * 1000),
                error=str(exc),
            )
            raise
        output_file.write_bytes(audio_bytes)

        elapsed = time.perf_counter() - start
        logger.info(
            "elevenlabs_synthesize_completed",
            voice_id=voice_id,
            latency_ms=int(elapsed * 1000),
            bytes_received=len(audio_bytes),
        )

        return AudioResult(
            audio_path=output_file,
            sample_rate=44100,
            format="mp3",
        )

    async def synthesize_with_word_boundaries(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> tuple[AudioResult, list[WordBoundary]]:
        """Synthesize text and return character-level timing data.

        Uses ElevenLabs convert_with_timestamps endpoint. The returned
        alignment data includes per-character start/end times in seconds;
        we convert to word-level WordBoundary objects by splitting on
        whitespace token boundaries.
        """
        client = self._get_client()
        model_id = self._get_model_id(settings_)
        voice_settings = self._build_voice_settings(settings_)

        logger.info(
            "elevenlabs_synthesize_with_timestamps_started",
            voice_id=voice_id,
            text_length=len(text),
        )
        start = time.perf_counter()

        def _synth():
            return client.text_to_speech.convert_with_timestamps(
                voice_id=voice_id,
                text=text,
                model_id=model_id,
                voice_settings=voice_settings,
            )

        try:
            result = await run_sync(_synth)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error(
                "elevenlabs_synthesize_with_timestamps_failed",
                voice_id=voice_id,
                latency_ms=int(elapsed * 1000),
                error=str(exc),
            )
            raise

        # Decode audio bytes
        import base64

        audio_bytes: bytes
        if hasattr(result, 'audio_base64') and result.audio_base64:
            audio_bytes = base64.b64decode(result.audio_base64)
        elif hasattr(result, 'audio') and result.audio:
            audio_bytes = result.audio if isinstance(result.audio, bytes) else bytes(result.audio)
        else:
            audio_bytes = b""

        output_file = self.prepare_output_path(prefix="elevenlabs_ts", ext="mp3")
        output_file.write_bytes(audio_bytes)

        # Parse alignment into WordBoundary objects
        word_boundaries: list[WordBoundary] = []
        alignment = getattr(result, 'alignment', None) or getattr(result, 'normalized_alignment', None)
        if alignment is not None:
            chars = getattr(alignment, 'characters', None) or []
            starts = getattr(alignment, 'character_start_times_seconds', None) or []
            ends = getattr(alignment, 'character_end_times_seconds', None) or []
            word_boundaries = _parse_word_boundaries(chars, starts, ends)

        elapsed = time.perf_counter() - start
        logger.info(
            "elevenlabs_synthesize_with_timestamps_completed",
            voice_id=voice_id,
            latency_ms=int(elapsed * 1000),
            word_count=len(word_boundaries),
        )

        audio_result = AudioResult(audio_path=output_file, sample_rate=44100, format="mp3")
        return audio_result, word_boundaries

    async def speech_to_speech(self, audio_path: Path, voice_id: str) -> Path:
        """Convert the voice in an audio file to a different ElevenLabs voice.

        Args:
            audio_path: Path to the source audio file.
            voice_id: Target ElevenLabs voice ID to convert to.

        Returns:
            Path to the output MP3 file.
        """
        client = self._get_client()
        logger.info("elevenlabs_sts_started", voice_id=voice_id, source=str(audio_path))
        start = time.perf_counter()

        def _convert():
            with open(audio_path, "rb") as f:
                result = client.speech_to_speech.convert(
                    voice_id=voice_id,
                    audio=f,
                    model_id="eleven_english_sts_v2",
                    output_format="mp3_44100_128",
                )
                return b"".join(result)

        try:
            audio_bytes = await run_sync(_convert)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error(
                "elevenlabs_sts_failed",
                voice_id=voice_id,
                latency_ms=int(elapsed * 1000),
                error=str(exc),
            )
            raise

        output_path = self.prepare_output_path(prefix="elevenlabs_sts", ext="mp3")
        output_path.write_bytes(audio_bytes)

        elapsed = time.perf_counter() - start
        logger.info(
            "elevenlabs_sts_completed",
            voice_id=voice_id,
            latency_ms=int(elapsed * 1000),
            bytes_received=len(audio_bytes),
        )
        return output_path

    async def isolate_audio(self, audio_path: Path) -> Path:
        """Remove background noise from an audio file using ElevenLabs Audio Isolation.

        Args:
            audio_path: Path to the noisy audio file.

        Returns:
            Path to the cleaned-up audio file (written alongside the original
            with an ``enhanced_`` prefix).
        """
        client = self._get_client()
        logger.info("elevenlabs_audio_isolation_started", source=str(audio_path))
        start = time.perf_counter()

        def _isolate():
            with open(audio_path, "rb") as f:
                result = client.audio_isolation.audio_isolation(audio=f)
                return b"".join(result)

        try:
            audio_bytes = await run_sync(_isolate)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error(
                "elevenlabs_audio_isolation_failed",
                latency_ms=int(elapsed * 1000),
                error=str(exc),
            )
            raise

        output = audio_path.parent / f"enhanced_{audio_path.name}"
        output.write_bytes(audio_bytes)

        elapsed = time.perf_counter() - start
        logger.info(
            "elevenlabs_audio_isolation_completed",
            output=str(output),
            latency_ms=int(elapsed * 1000),
            bytes_received=len(audio_bytes),
        )
        return output

    async def design_voice(self, description: str, text: str = "") -> dict:
        """Generate voice previews from a text description.

        Args:
            description: Natural-language description of the desired voice
                (e.g. "A deep, calm male narrator with a slight British accent").
            text: Optional sample text for the preview. A generic sentence is
                used when omitted.

        Returns:
            A dict with key ``previews``, each entry containing:
            - ``voice_id``: the generated voice ID
            - ``audio_base64``: base64-encoded MP3 preview audio
        """
        client = self._get_client()
        logger.info("elevenlabs_design_voice_started", description=description[:80])

        preview_text = text or "Hello, this is a preview of the designed voice."

        def _design():
            return client.text_to_voice.create_previews(
                voice_description=description,
                text=preview_text,
            )

        try:
            result = await run_sync(_design)
        except Exception as exc:
            logger.error("elevenlabs_design_voice_failed", error=str(exc))
            raise

        previews = [
            {
                "voice_id": p.generated_voice_id,
                "audio_base64": p.audio_base64,
            }
            for p in result.previews
        ]
        logger.info("elevenlabs_design_voice_completed", preview_count=len(previews))
        return {"previews": previews}

    async def generate_sound_effect(self, description: str, duration: float = 5.0) -> Path:
        """Generate a sound effect from a text description.

        Args:
            description: Text describing the sound effect
                (e.g. "Thunderstorm with heavy rain and distant thunder").
            duration: Desired duration in seconds (1–22). Defaults to 5.0.

        Returns:
            Path to the generated MP3 file.
        """
        client = self._get_client()
        logger.info(
            "elevenlabs_sfx_started",
            description=description[:80],
            duration=duration,
        )
        start = time.perf_counter()

        def _gen():
            result = client.text_to_sound_effects.convert(
                text=description,
                duration_seconds=duration,
                prompt_influence=0.3,
            )
            return b"".join(result)

        try:
            audio_bytes = await run_sync(_gen)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error(
                "elevenlabs_sfx_failed",
                latency_ms=int(elapsed * 1000),
                error=str(exc),
            )
            raise

        output_path = self.prepare_output_path(prefix="elevenlabs_sfx", ext="mp3")
        output_path.write_bytes(audio_bytes)

        elapsed = time.perf_counter() - start
        logger.info(
            "elevenlabs_sfx_completed",
            latency_ms=int(elapsed * 1000),
            bytes_received=len(audio_bytes),
        )
        return output_path

    async def clone_voice(
        self, samples: list[ProviderAudioSample], config: CloneConfig
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
                    remove_background_noise=True,
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
        self, model_id: str, samples: list[ProviderAudioSample], config: FineTuneConfig
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
                    logger.info("elevenlabs_voices_listed", count=len(voices), source="api")
                    return voices
        except Exception as exc:
            logger.debug("elevenlabs_live_list_failed", error=str(exc))

        # Fallback: hardcoded premade voices
        fallback = self._hardcoded_premade_voices()
        logger.info("elevenlabs_voices_listed", count=len(fallback), source="hardcoded")
        return fallback

    @staticmethod
    def _hardcoded_premade_voices() -> list[VoiceInfo]:
        """ElevenLabs' premade voices available to all tiers.

        Voice data is loaded from ``data/elevenlabs_voices.json`` and cached
        at the module level so the file is only read once per process.
        """
        global _premade_voices_cache  # noqa: PLW0603
        if _premade_voices_cache is not None:
            return _premade_voices_cache

        voices_path = Path(__file__).parent / "data" / "elevenlabs_voices.json"
        with open(voices_path, encoding="utf-8") as fh:
            entries = json.load(fh)

        _premade_voices_cache = [
            VoiceInfo(
                voice_id=e["voice_id"],
                name=e["name"],
                language="en",
                gender=e.get("gender"),
                description=(
                    f"{e['accent']} accent, {e['use_case']}"
                    if e.get("accent")
                    else e["use_case"]
                ),
            )
            for e in entries
        ]
        return _premade_voices_cache

    async def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_cloning=True,
            supports_fine_tuning=False,
            supports_streaming=True,
            supports_ssml=False,
            supports_zero_shot=False,
            supports_batch=True,
            supports_word_boundaries=True,
            supports_pronunciation_assessment=False,
            supports_transcription=False,
            requires_gpu=False,
            gpu_mode="none",
            min_samples_for_cloning=1,
            max_text_length=5000,
            supported_languages=[
                "en", "es", "fr", "de", "it", "pt", "pl", "hi",
                "ar", "zh", "ja", "ko", "nl", "ru", "sv", "tr",
            ],
            supported_output_formats=["mp3", "wav"],
        )

    async def health_check(self) -> ProviderHealth:
        start = time.perf_counter()
        try:
            api_key = self.get_config_value('api_key', settings.elevenlabs_api_key)
            if not api_key:
                from elevenlabs.client import ElevenLabs as _EL  # noqa: F401

                latency = int((time.perf_counter() - start) * 1000)
                logger.info("elevenlabs_health_check", healthy=True, latency_ms=latency, note="no_api_key")
                return ProviderHealth(
                    name="elevenlabs",
                    healthy=True,
                    latency_ms=latency,
                    error="SDK ready — configure API key in Providers settings",
                )
            client = self._get_client()
            await run_sync(client.voices.get_all)
            latency = int((time.perf_counter() - start) * 1000)
            logger.info("elevenlabs_health_check", healthy=True, latency_ms=latency)
            return ProviderHealth(name="elevenlabs", healthy=True, latency_ms=latency)
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            logger.info("elevenlabs_health_check", healthy=False, latency_ms=latency, error=str(e))
            return ProviderHealth(name="elevenlabs", healthy=False, latency_ms=latency, error=str(e))

    async def stream_synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AsyncIterator[bytes]:
        import asyncio
        import concurrent.futures

        client = self._get_client()
        model_id = self._get_model_id(settings_)
        voice_settings = self._build_voice_settings(settings_)

        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _produce():
            try:
                for chunk in client.text_to_speech.convert(
                    voice_id=voice_id,
                    text=text,
                    model_id=model_id,
                    output_format="mp3_44100_128",
                    voice_settings=voice_settings,
                ):
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, e)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            executor.submit(_produce)

            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                yield item
        finally:
            executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _parse_word_boundaries(
    chars: list[str],
    starts: list[float],
    ends: list[float],
) -> list[WordBoundary]:
    """Convert ElevenLabs character-level alignment into word-level WordBoundary objects.

    ElevenLabs returns per-character timing. This groups consecutive
    non-space characters into words and uses the first character's start
    time and the last character's end time for each word boundary.

    Args:
        chars: List of characters in the output.
        starts: Per-character start times in seconds.
        ends: Per-character end times in seconds.

    Returns:
        List of WordBoundary objects, one per whitespace-delimited word.
    """
    if not chars or len(chars) != len(starts) or len(chars) != len(ends):
        return []

    boundaries: list[WordBoundary] = []
    word_chars: list[str] = []
    word_start: float | None = None
    word_end: float = 0.0
    word_index = 0

    for ch, t_start, t_end in zip(chars, starts, ends):
        if ch in (" ", "\t", "\n"):
            if word_chars:
                boundaries.append(WordBoundary(
                    text="".join(word_chars),
                    offset_ms=int((word_start or 0) * 1000),
                    duration_ms=int((word_end - (word_start or 0)) * 1000),
                    word_index=word_index,
                ))
                word_index += 1
                word_chars = []
                word_start = None
        else:
            if word_start is None:
                word_start = t_start
            word_chars.append(ch)
            word_end = t_end

    # Flush trailing word
    if word_chars:
        boundaries.append(WordBoundary(
            text="".join(word_chars),
            offset_ms=int((word_start or 0) * 1000),
            duration_ms=int((word_end - (word_start or 0)) * 1000),
            word_index=word_index,
        ))

    return boundaries
