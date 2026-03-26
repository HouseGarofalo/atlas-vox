"""Piper TTS provider — lightweight ONNX-based, Home Assistant compatible."""

from __future__ import annotations

import json
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

# Well-known Piper voices for bootstrapping — all English voice models
DEFAULT_PIPER_VOICES = [
    # en_US (American English) — 20 voices
    {"id": "en_US-amy-low", "name": "Amy (US Low)", "lang": "en", "gender": "Female"},
    {"id": "en_US-amy-medium", "name": "Amy (US Medium)", "lang": "en", "gender": "Female"},
    {"id": "en_US-arctic-medium", "name": "Arctic (US Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_US-bryce-medium", "name": "Bryce (US Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_US-danny-low", "name": "Danny (US Low)", "lang": "en", "gender": "Male"},
    {"id": "en_US-hfc_female-medium", "name": "HFC Female (US Medium)", "lang": "en", "gender": "Female"},
    {"id": "en_US-hfc_male-medium", "name": "HFC Male (US Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_US-joe-medium", "name": "Joe (US Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_US-john-medium", "name": "John (US Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_US-kathleen-low", "name": "Kathleen (US Low)", "lang": "en", "gender": "Female"},
    {"id": "en_US-kristin-medium", "name": "Kristin (US Medium)", "lang": "en", "gender": "Female"},
    {"id": "en_US-kusal-medium", "name": "Kusal (US Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_US-l2arctic-medium", "name": "L2Arctic (US Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_US-lessac-low", "name": "Lessac (US Low)", "lang": "en", "gender": "Male"},
    {"id": "en_US-lessac-medium", "name": "Lessac (US Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_US-lessac-high", "name": "Lessac (US High)", "lang": "en", "gender": "Male"},
    {"id": "en_US-libritts-high", "name": "LibriTTS (US High)", "lang": "en", "gender": "Male"},
    {"id": "en_US-libritts_r-medium", "name": "LibriTTS-R (US Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_US-ljspeech-medium", "name": "LJSpeech (US Medium)", "lang": "en", "gender": "Female"},
    {"id": "en_US-ljspeech-high", "name": "LJSpeech (US High)", "lang": "en", "gender": "Female"},
    {"id": "en_US-norman-medium", "name": "Norman (US Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_US-reza_ibrahim-medium", "name": "Reza Ibrahim (US Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_US-ryan-low", "name": "Ryan (US Low)", "lang": "en", "gender": "Male"},
    {"id": "en_US-ryan-medium", "name": "Ryan (US Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_US-ryan-high", "name": "Ryan (US High)", "lang": "en", "gender": "Male"},
    {"id": "en_US-sam-medium", "name": "Sam (US Medium)", "lang": "en", "gender": "Male"},
    # en_GB (British English) — 9 voices
    {"id": "en_GB-alan-low", "name": "Alan (GB Low)", "lang": "en", "gender": "Male"},
    {"id": "en_GB-alan-medium", "name": "Alan (GB Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_GB-alba-medium", "name": "Alba (GB Medium)", "lang": "en", "gender": "Female"},
    {"id": "en_GB-aru-medium", "name": "Aru (GB Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_GB-cori-medium", "name": "Cori (GB Medium)", "lang": "en", "gender": "Female"},
    {"id": "en_GB-cori-high", "name": "Cori (GB High)", "lang": "en", "gender": "Female"},
    {"id": "en_GB-jenny_dioco-medium", "name": "Jenny Dioco (GB Medium)", "lang": "en", "gender": "Female"},
    {"id": "en_GB-northern_english_male-medium", "name": "Northern English Male (GB Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_GB-semaine-medium", "name": "Semaine (GB Medium)", "lang": "en", "gender": "Male"},
    {"id": "en_GB-southern_english_female-low", "name": "Southern English Female (GB Low)", "lang": "en", "gender": "Female"},
    {"id": "en_GB-vctk-medium", "name": "VCTK (GB Medium)", "lang": "en", "gender": "Male"},
    # Popular non-English voices
    {"id": "de_DE-thorsten-medium", "name": "Thorsten (DE Medium)", "lang": "de", "gender": "Male"},
    {"id": "fr_FR-siwis-medium", "name": "Siwis (FR Medium)", "lang": "fr", "gender": "Female"},
    {"id": "es_ES-davefx-medium", "name": "Davefx (ES Medium)", "lang": "es", "gender": "Male"},
]


class PiperTTSProvider(TTSProvider):
    """Piper TTS — fast ONNX inference, CPU-only, Home Assistant compatible."""

    def __init__(self) -> None:
        self._piper = None
        self._model_dir = Path(settings.piper_model_path)

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._piper = None
        model_path = self.get_config_value('model_path', str(settings.piper_model_path))
        self._model_dir = Path(model_path)

    def _get_piper(self, model_path: str | None = None):
        """Lazy-load the Piper voice."""
        try:
            from piper import PiperVoice
        except ImportError:
            logger.error("piper_not_installed", hint="pip install piper-tts")
            raise

        if model_path:
            return PiperVoice.load(model_path)

        if self._piper is None:
            # Try loading default model
            default_model = self._model_dir / "en_US-lessac-medium.onnx"
            if default_model.exists():
                self._piper = PiperVoice.load(str(default_model))
                logger.info("piper_loaded", model=str(default_model))
            else:
                logger.warning("piper_no_default_model", path=str(default_model))
                raise FileNotFoundError(
                    f"Default Piper model not found at {default_model}. "
                    f"Download from https://github.com/rhasspy/piper/releases"
                )
        return self._piper

    def _discover_models(self) -> list[dict]:
        """Find all .onnx model files in the model directory."""
        models = []
        if self._model_dir.exists():
            for onnx_file in self._model_dir.glob("*.onnx"):
                config_file = onnx_file.with_suffix(".onnx.json")
                name = onnx_file.stem
                lang = name.split("-")[0] if "-" in name else "en"

                info = {"id": name, "path": str(onnx_file), "lang": lang}
                if config_file.exists():
                    try:
                        with open(config_file) as f:
                            config = json.load(f)
                        info["sample_rate"] = config.get("audio", {}).get("sample_rate", 22050)
                    except Exception:
                        pass
                models.append(info)
        return models

    async def synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AudioResult:
        """Synthesize text with Piper."""
        output_dir = Path(settings.storage_path) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"piper_{uuid.uuid4().hex[:12]}.wav"

        start = time.perf_counter()

        # Check if voice_id is a path to a specific model
        model_path = None
        candidate = self._model_dir / f"{voice_id}.onnx"
        if candidate.exists():
            model_path = str(candidate)

        voice = self._get_piper(model_path)

        def _synth():
            import io
            import wave
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(voice.config.sample_rate if hasattr(voice, 'config') and hasattr(voice.config, 'sample_rate') else 22050)
                voice.synthesize(text, wav)
            buf.seek(0)
            output_file.write_bytes(buf.read())

        await run_sync(_synth)

        elapsed = time.perf_counter() - start
        logger.info("piper_synthesis_complete", voice=voice_id, latency_ms=int(elapsed * 1000))

        return AudioResult(
            audio_path=output_file,
            sample_rate=22050,
            format="wav",
        )

    async def clone_voice(
        self, samples: list[AudioSample], config: CloneConfig
    ) -> VoiceModel:
        """Piper does not support zero-shot voice cloning."""
        raise NotImplementedError(
            "Piper does not support voice cloning. "
            "Use Piper's training pipeline to create custom voices."
        )

    async def fine_tune(
        self, model_id: str, samples: list[AudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        """Piper fine-tuning is not supported through this provider.

        Piper custom voices require the external piper-recording-studio and
        piper-train toolchain.  See https://github.com/rhasspy/piper/blob/master/TRAINING.md
        for instructions on training a custom voice offline.
        """
        raise NotImplementedError(
            "Piper fine-tuning requires the external piper-train toolchain and is not "
            "available through this API. See https://github.com/rhasspy/piper/blob/master/TRAINING.md"
        )

    async def list_voices(self) -> list[VoiceInfo]:
        """List available Piper voices from local models + defaults."""
        voices = []

        # Discover local ONNX models
        for model in self._discover_models():
            voices.append(VoiceInfo(
                voice_id=model["id"],
                name=model["id"].replace("-", " ").replace("_", " ").title(),
                language=model["lang"],
                description=f"Local Piper model: {model['path']}",
            ))

        # Add defaults if no local models found
        if not voices:
            for v in DEFAULT_PIPER_VOICES:
                voices.append(VoiceInfo(
                    voice_id=v["id"],
                    name=v["name"],
                    language=v["lang"],
                    gender=v.get("gender"),
                    description="Download from https://github.com/rhasspy/piper/releases",
                ))

        return voices

    async def get_capabilities(self) -> ProviderCapabilities:
        # Piper fine-tuning requires the external piper-recording-studio + piper-train
        # toolchain which is not integrated into this provider.  Reporting
        # supports_fine_tuning=True would mislead the UI into showing a training
        # workflow that cannot complete through this API.
        return ProviderCapabilities(
            supports_cloning=False,
            supports_fine_tuning=False,
            supports_streaming=False,
            supports_ssml=False,
            supports_zero_shot=False,
            supports_batch=True,
            requires_gpu=False,
            gpu_mode="none",
            min_samples_for_cloning=0,
            max_text_length=5000,
            supported_languages=["en", "de", "fr", "es", "it", "nl", "pt", "pl",
                                 "ru", "uk", "zh", "ar", "fi", "sv", "no", "da"],
            supported_output_formats=["wav"],
        )

    async def health_check(self) -> ProviderHealth:
        start = time.perf_counter()
        try:
            # Check if at least one model exists
            models = self._discover_models()
            if models:
                self._get_piper(models[0]["path"])
            else:
                # Still healthy if piper is installed, just no models downloaded
                from piper import PiperVoice  # noqa: F401
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(
                name="piper",
                healthy=True,
                latency_ms=latency,
                error=None if models else "No models downloaded — see piper_model_path",
            )
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(name="piper", healthy=False, latency_ms=latency, error=str(e))
