"""Kokoro TTS provider — lightweight, CPU-only, 54 built-in voices."""

from __future__ import annotations

import io
import time
from collections.abc import AsyncIterator

import structlog

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


class KokoroTTSProvider(TTSProvider):
    """Kokoro TTS — 82M params, fast CPU inference, 54 voices."""

    def __init__(self) -> None:
        self._pipeline = None
        self._voices: list[VoiceInfo] | None = None

    def configure(self, config: dict) -> None:
        super().configure(config)

    def _get_pipeline(self):
        """Lazy-load the Kokoro pipeline."""
        if self._pipeline is None:
            try:
                from kokoro import KPipeline
                self._pipeline = KPipeline(lang_code="a")  # American English
                logger.info("kokoro_pipeline_loaded")
            except ImportError:
                logger.error("kokoro_not_installed", hint="pip install kokoro>=0.9.4")
                raise
        return self._pipeline

    async def synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AudioResult:
        """Generate speech from text using Kokoro."""
        pipeline = self._get_pipeline()
        output_file = self.prepare_output_path(prefix="kokoro")

        logger.info("kokoro_synthesize_started", voice_id=voice_id, text_length=len(text))
        start = time.perf_counter()

        def _synth():
            gen = pipeline(text, voice=voice_id, speed=settings_.speed)
            import numpy as np
            import soundfile as sf
            chunks = [audio for _gs, _ps, audio in gen]
            if not chunks:
                raise RuntimeError("Kokoro produced no audio output")
            full = np.concatenate(chunks)
            sf.write(str(output_file), full, 24000)
            return full

        try:
            full_audio = await run_sync(_synth)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error("kokoro_synthesize_failed", voice_id=voice_id, latency_ms=int(elapsed * 1000), error=str(exc))
            raise
        sample_rate = 24000

        duration = len(full_audio) / sample_rate
        elapsed = time.perf_counter() - start
        logger.info(
            "kokoro_synthesize_completed",
            voice_id=voice_id,
            duration_seconds=duration,
            latency_ms=int(elapsed * 1000),
        )

        return AudioResult(
            audio_path=output_file,
            duration_seconds=duration,
            sample_rate=sample_rate,
            format="wav",
        )

    async def clone_voice(
        self, samples: list[ProviderAudioSample], config: CloneConfig
    ) -> VoiceModel:
        """Kokoro does not support voice cloning."""
        raise NotImplementedError("Kokoro does not support voice cloning")

    async def fine_tune(
        self, model_id: str, samples: list[ProviderAudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        """Kokoro does not support fine-tuning."""
        raise NotImplementedError("Kokoro does not support fine-tuning")

    async def list_voices(self) -> list[VoiceInfo]:
        """List all 54 Kokoro built-in voices across 9 languages."""
        if self._voices is not None:
            logger.debug("kokoro_voices_listed", count=len(self._voices), cached=True)
            return self._voices

        # Kokoro voice naming convention:
        #   First letter: language (a=American, b=British, j=Japanese, z=Chinese,
        #                           e=Spanish, f=French, h=Hindi, i=Italian, p=Portuguese)
        #   Second letter: gender (f=female, m=male)
        #   Underscore + name
        default_voices = [
            # --- American English Female (af_) --- 14 voices
            VoiceInfo(voice_id="af_heart", name="Heart (American Female)", language="en", gender="Female"),
            VoiceInfo(voice_id="af_alloy", name="Alloy (American Female)", language="en", gender="Female"),
            VoiceInfo(voice_id="af_aoede", name="Aoede (American Female)", language="en", gender="Female"),
            VoiceInfo(voice_id="af_bella", name="Bella (American Female)", language="en", gender="Female"),
            VoiceInfo(voice_id="af_jessica", name="Jessica (American Female)", language="en", gender="Female"),
            VoiceInfo(voice_id="af_kore", name="Kore (American Female)", language="en", gender="Female"),
            VoiceInfo(voice_id="af_nicole", name="Nicole (American Female)", language="en", gender="Female"),
            VoiceInfo(voice_id="af_nova", name="Nova (American Female)", language="en", gender="Female"),
            VoiceInfo(voice_id="af_river", name="River (American Female)", language="en", gender="Female"),
            VoiceInfo(voice_id="af_sarah", name="Sarah (American Female)", language="en", gender="Female"),
            VoiceInfo(voice_id="af_sky", name="Sky (American Female)", language="en", gender="Female"),
            # --- American English Male (am_) --- 9 voices
            VoiceInfo(voice_id="am_adam", name="Adam (American Male)", language="en", gender="Male"),
            VoiceInfo(voice_id="am_echo", name="Echo (American Male)", language="en", gender="Male"),
            VoiceInfo(voice_id="am_eric", name="Eric (American Male)", language="en", gender="Male"),
            VoiceInfo(voice_id="am_fenrir", name="Fenrir (American Male)", language="en", gender="Male"),
            VoiceInfo(voice_id="am_liam", name="Liam (American Male)", language="en", gender="Male"),
            VoiceInfo(voice_id="am_michael", name="Michael (American Male)", language="en", gender="Male"),
            VoiceInfo(voice_id="am_onyx", name="Onyx (American Male)", language="en", gender="Male"),
            VoiceInfo(voice_id="am_puck", name="Puck (American Male)", language="en", gender="Male"),
            VoiceInfo(voice_id="am_santa", name="Santa (American Male)", language="en", gender="Male"),
            # --- British English Female (bf_) --- 4 voices
            VoiceInfo(voice_id="bf_alice", name="Alice (British Female)", language="en", gender="Female"),
            VoiceInfo(voice_id="bf_emma", name="Emma (British Female)", language="en", gender="Female"),
            VoiceInfo(voice_id="bf_isabella", name="Isabella (British Female)", language="en", gender="Female"),
            VoiceInfo(voice_id="bf_lily", name="Lily (British Female)", language="en", gender="Female"),
            # --- British English Male (bm_) --- 4 voices
            VoiceInfo(voice_id="bm_daniel", name="Daniel (British Male)", language="en", gender="Male"),
            VoiceInfo(voice_id="bm_fable", name="Fable (British Male)", language="en", gender="Male"),
            VoiceInfo(voice_id="bm_george", name="George (British Male)", language="en", gender="Male"),
            VoiceInfo(voice_id="bm_lewis", name="Lewis (British Male)", language="en", gender="Male"),
            # --- Japanese (jf_/jm_) --- 5 voices
            VoiceInfo(voice_id="jf_alpha", name="Alpha (Japanese Female)", language="ja", gender="Female"),
            VoiceInfo(voice_id="jf_gongitsune", name="Gongitsune (Japanese Female)", language="ja", gender="Female"),
            VoiceInfo(voice_id="jf_nezumi", name="Nezumi (Japanese Female)", language="ja", gender="Female"),
            VoiceInfo(voice_id="jf_tebukuro", name="Tebukuro (Japanese Female)", language="ja", gender="Female"),
            VoiceInfo(voice_id="jm_kumo", name="Kumo (Japanese Male)", language="ja", gender="Male"),
            # --- Mandarin Chinese (zf_/zm_) --- 8 voices
            VoiceInfo(voice_id="zf_xiaobei", name="Xiaobei (Chinese Female)", language="zh", gender="Female"),
            VoiceInfo(voice_id="zf_xiaoni", name="Xiaoni (Chinese Female)", language="zh", gender="Female"),
            VoiceInfo(voice_id="zf_xiaoxiao", name="Xiaoxiao (Chinese Female)", language="zh", gender="Female"),
            VoiceInfo(voice_id="zf_xiaoyi", name="Xiaoyi (Chinese Female)", language="zh", gender="Female"),
            VoiceInfo(voice_id="zm_yunjian", name="Yunjian (Chinese Male)", language="zh", gender="Male"),
            VoiceInfo(voice_id="zm_yunxi", name="Yunxi (Chinese Male)", language="zh", gender="Male"),
            VoiceInfo(voice_id="zm_yunxia", name="Yunxia (Chinese Male)", language="zh", gender="Male"),
            VoiceInfo(voice_id="zm_yunyang", name="Yunyang (Chinese Male)", language="zh", gender="Male"),
            # --- Spanish (ef_/em_) --- 3 voices
            VoiceInfo(voice_id="ef_dora", name="Dora (Spanish Female)", language="es", gender="Female"),
            VoiceInfo(voice_id="em_alex", name="Alex (Spanish Male)", language="es", gender="Male"),
            VoiceInfo(voice_id="em_santa", name="Santa (Spanish Male)", language="es", gender="Male"),
            # --- French (ff_) --- 1 voice
            VoiceInfo(voice_id="ff_siwis", name="Siwis (French Female)", language="fr", gender="Female"),
            # --- Hindi (hf_/hm_) --- 4 voices
            VoiceInfo(voice_id="hf_alpha", name="Alpha (Hindi Female)", language="hi", gender="Female"),
            VoiceInfo(voice_id="hf_beta", name="Beta (Hindi Female)", language="hi", gender="Female"),
            VoiceInfo(voice_id="hm_omega", name="Omega (Hindi Male)", language="hi", gender="Male"),
            VoiceInfo(voice_id="hm_psi", name="Psi (Hindi Male)", language="hi", gender="Male"),
            # --- Italian (if_/im_) --- 2 voices
            VoiceInfo(voice_id="if_sara", name="Sara (Italian Female)", language="it", gender="Female"),
            VoiceInfo(voice_id="im_nicola", name="Nicola (Italian Male)", language="it", gender="Male"),
            # --- Brazilian Portuguese (pf_/pm_) --- 3 voices
            VoiceInfo(voice_id="pf_dora", name="Dora (Portuguese Female)", language="pt", gender="Female"),
            VoiceInfo(voice_id="pm_alex", name="Alex (Portuguese Male)", language="pt", gender="Male"),
            VoiceInfo(voice_id="pm_santa", name="Santa (Portuguese Male)", language="pt", gender="Male"),
        ]
        self._voices = default_voices
        logger.info("kokoro_voices_listed", count=len(self._voices), cached=False)
        return self._voices

    def _iter_stream_chunks(
        self,
        text: str,
        voice_id: str,
        speed: float,
        queue: "asyncio.Queue[bytes | None]",
        loop: "asyncio.AbstractEventLoop",
    ) -> None:
        """Iterate Kokoro pipeline chunks in a thread, pushing each WAV buffer to the queue.

        The Kokoro pipeline yields (grapheme_str, phoneme_str, audio_ndarray) tuples,
        one per sentence segment.  We encode each segment independently so the caller
        receives audio as soon as each segment is ready rather than waiting for the
        entire generation to complete.
        """
        import soundfile as sf

        pipeline = self._get_pipeline()
        try:
            for _gs, _ps, audio in pipeline(text, voice=voice_id, speed=speed):
                buf = io.BytesIO()
                sf.write(buf, audio, 24000, format="WAV")
                loop.call_soon_threadsafe(queue.put_nowait, buf.getvalue())
        except Exception as exc:
            logger.error("kokoro_stream_chunk_error", error=str(exc))
            raise
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    async def stream_synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AsyncIterator[bytes]:
        """Stream synthesis — yields one WAV buffer per sentence segment as Kokoro produces it."""
        import asyncio

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        logger.info("kokoro_stream_started", voice_id=voice_id, text_length=len(text))
        future = loop.run_in_executor(
            None,
            self._iter_stream_chunks,
            text,
            voice_id,
            settings_.speed,
            queue,
            loop,
        )
        try:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            await future

    async def get_capabilities(self) -> ProviderCapabilities:
        """Kokoro capabilities: CPU-only, no cloning, streaming supported."""
        return ProviderCapabilities(
            supports_cloning=False,
            supports_fine_tuning=False,
            supports_streaming=True,
            supports_ssml=False,
            supports_zero_shot=False,
            supports_batch=True,
            requires_gpu=False,
            gpu_mode="none",
            min_samples_for_cloning=0,
            max_text_length=5000,
            supported_languages=["en", "ja", "zh", "es", "fr", "hi", "it", "pt"],
            supported_output_formats=["wav"],
        )

    async def health_check(self) -> ProviderHealth:
        """Check if Kokoro is installed and usable."""
        start = time.perf_counter()
        try:
            self._get_pipeline()
            latency = int((time.perf_counter() - start) * 1000)
            logger.info("kokoro_health_check", healthy=True, latency_ms=latency)
            return ProviderHealth(name="kokoro", healthy=True, latency_ms=latency)
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            logger.info("kokoro_health_check", healthy=False, latency_ms=latency, error=str(e))
            return ProviderHealth(
                name="kokoro", healthy=False, latency_ms=latency, error=str(e)
            )
