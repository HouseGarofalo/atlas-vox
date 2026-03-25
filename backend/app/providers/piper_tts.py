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

# Well-known Piper voices for bootstrapping
DEFAULT_PIPER_VOICES = [
    {"id": "en_US-lessac-medium", "name": "Lessac (US Medium)", "lang": "en"},
    {"id": "en_US-amy-medium", "name": "Amy (US Medium)", "lang": "en"},
    {"id": "en_US-ryan-medium", "name": "Ryan (US Medium)", "lang": "en"},
    {"id": "en_US-arctic-medium", "name": "Arctic (US Medium)", "lang": "en"},
    {"id": "en_GB-alan-medium", "name": "Alan (GB Medium)", "lang": "en"},
    {"id": "en_GB-cori-medium", "name": "Cori (GB Medium)", "lang": "en"},
    {"id": "de_DE-thorsten-medium", "name": "Thorsten (DE Medium)", "lang": "de"},
    {"id": "fr_FR-siwis-medium", "name": "Siwis (FR Medium)", "lang": "fr"},
    {"id": "es_ES-davefx-medium", "name": "Davefx (ES Medium)", "lang": "es"},
]


class PiperTTSProvider(TTSProvider):
    """Piper TTS — fast ONNX inference, CPU-only, Home Assistant compatible."""

    def __init__(self) -> None:
        self._piper = None
        self._model_dir = Path(settings.piper_model_path)

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
        """Fine-tune a Piper voice (via external training pipeline).

        NOTE: Piper fine-tuning uses a separate training pipeline
        (piper-recording-studio + piper-train). This method creates
        the necessary metadata for tracking but actual training
        happens externally.
        """
        model_dir = Path(settings.storage_path) / "models" / "piper" / f"ft_{uuid.uuid4().hex[:8]}"
        model_dir.mkdir(parents=True, exist_ok=True)

        ft_model_id = uuid.uuid4().hex[:12]
        logger.info(
            "piper_fine_tune_prepared",
            model_id=ft_model_id,
            samples=len(samples),
        )

        return VoiceModel(
            model_id=ft_model_id,
            model_path=model_dir,
            provider_model_id=str(model_dir),
            metrics={
                "method": "piper_train",
                "samples_count": len(samples),
                "note": "Training via external piper-train pipeline",
            },
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
                    description="Download from https://github.com/rhasspy/piper/releases",
                ))

        return voices

    async def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_cloning=False,
            supports_fine_tuning=True,
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
