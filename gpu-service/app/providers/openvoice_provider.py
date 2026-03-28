"""OpenVoice v2 GPU provider.

Requires the ``MyShell-OpenVoice`` package (``pip install -e .`` from the
OpenVoice repository checkout).  OpenVoice performs instant voice tone
cloning from short reference audio.

Architecture overview:
  1. **Base TTS** generates speech from text with a default speaker identity.
     - Preferred: MeloTTS (``pip install melotts``) — multi-lingual, V2 quality.
     - Fallback: OpenVoice V1 ``BaseSpeakerTTS`` — English and Chinese only.
  2. **ToneColorConverter** applies tone-color from a reference speaker onto the
     base speech, producing the cloned output.

Model checkpoints are downloaded from HuggingFace on first ``load()``:
  - V2 converter + base speaker embeddings: ``myshell-ai/OpenVoiceV2``
  - V1 base speaker TTS (fallback): ``myshell-ai/OpenVoice``
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import structlog

from app.providers.base import GPUProviderBase

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Gate imports.
# ---------------------------------------------------------------------------
try:
    from openvoice.api import ToneColorConverter  # type: ignore[import-untyped]

    _OPENVOICE_AVAILABLE = True
except ImportError:
    _OPENVOICE_AVAILABLE = False

try:
    from melo.api import TTS as MeloTTS  # type: ignore[import-untyped]

    _MELOTTS_AVAILABLE = True
except ImportError:
    _MELOTTS_AVAILABLE = False

# HuggingFace repos
_HF_V2_REPO = "myshell-ai/OpenVoiceV2"
_HF_V1_REPO = "myshell-ai/OpenVoice"

# Local cache directories (relative to working directory / storage_path)
_V2_MODEL_DIR = Path("storage/models/openvoice_v2")
_V1_MODEL_DIR = Path("storage/models/openvoice_v1")


class OpenVoiceProvider(GPUProviderBase):
    """OpenVoice v2 — instant voice tone cloning."""

    name = "openvoice_v2"
    display_name = "OpenVoice v2"

    def __init__(self) -> None:
        self._tone_converter: Any = None
        self._base_tts: Any = None  # MeloTTS or BaseSpeakerTTS
        self._base_tts_type: str = ""  # "melo" or "v1"
        self._device: str = "cuda:0"
        self._v2_dir: Path = _V2_MODEL_DIR
        self._v1_dir: Path = _V1_MODEL_DIR
        self._base_speaker_se: dict[str, Any] = {}  # lang -> SE tensor
        self._cloned_voices: dict[str, dict] = {}  # voice_id -> metadata + SE tensor
        self._sample_rate: int = 22050

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self, device: str = "cuda:0") -> None:
        if not _OPENVOICE_AVAILABLE:
            raise RuntimeError(
                "openvoice is not installed. Clone the repo and run: pip install -e ."
            )

        self._device = device
        logger.info("openvoice.loading", device=device)

        try:
            import io
            import sys

            import torch
            from huggingface_hub import snapshot_download
            from openvoice.api import ToneColorConverter  # type: ignore[import-untyped]

            # Work around a Windows cp1252 encoding issue in OpenVoice's
            # text/__init__.py which calls ``print(clean_text)`` with IPA
            # characters.  Force UTF-8 stdout/stderr when they don't support it.
            if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
                try:
                    sys.stdout = io.TextIOWrapper(
                        sys.stdout.buffer, encoding="utf-8", errors="replace"
                    )
                    sys.stderr = io.TextIOWrapper(
                        sys.stderr.buffer, encoding="utf-8", errors="replace"
                    )
                except Exception:
                    pass

            # ----------------------------------------------------------
            # Step 1: Download V2 converter checkpoints.
            # ----------------------------------------------------------
            self._v2_dir = Path(
                snapshot_download(_HF_V2_REPO, local_dir=str(_V2_MODEL_DIR))
            )
            logger.info("openvoice.v2_model_dir", path=str(self._v2_dir))

            converter_config = self._v2_dir / "converter" / "config.json"
            converter_ckpt = self._v2_dir / "converter" / "checkpoint.pth"

            if not converter_config.exists() or not converter_ckpt.exists():
                raise FileNotFoundError(
                    f"OpenVoice V2 converter checkpoints not found at {self._v2_dir / 'converter'}. "
                    "Ensure the HuggingFace download completed successfully."
                )

            # ----------------------------------------------------------
            # Step 2: Load the ToneColorConverter.
            # ----------------------------------------------------------
            self._tone_converter = ToneColorConverter(
                str(converter_config),
                device=device,
            )
            self._tone_converter.load_ckpt(str(converter_ckpt))
            logger.info("openvoice.converter_loaded")

            # ----------------------------------------------------------
            # Step 3: Load pre-computed base speaker SE embeddings (V2).
            # ----------------------------------------------------------
            ses_dir = self._v2_dir / "base_speakers" / "ses"
            if ses_dir.is_dir():
                for se_file in ses_dir.glob("*.pth"):
                    lang_key = se_file.stem  # e.g., "en-default", "zh", "fr"
                    self._base_speaker_se[lang_key] = torch.load(
                        se_file, map_location=device, weights_only=True,
                    )
                    logger.info("openvoice.loaded_base_se", lang=lang_key)

            # ----------------------------------------------------------
            # Step 4: Load the base TTS model.
            # ----------------------------------------------------------
            if _MELOTTS_AVAILABLE:
                self._base_tts = MeloTTS(language="EN", device=device)
                self._base_tts_type = "melo"
                logger.info("openvoice.base_tts", type="MeloTTS")
            else:
                # Fallback: OpenVoice V1 BaseSpeakerTTS (English + Chinese)
                from openvoice.api import BaseSpeakerTTS  # type: ignore[import-untyped]

                self._v1_dir = Path(
                    snapshot_download(_HF_V1_REPO, local_dir=str(_V1_MODEL_DIR))
                )
                logger.info("openvoice.v1_model_dir", path=str(self._v1_dir))

                v1_en_config = self._v1_dir / "checkpoints" / "base_speakers" / "EN" / "config.json"
                v1_en_ckpt = self._v1_dir / "checkpoints" / "base_speakers" / "EN" / "checkpoint.pth"

                if not v1_en_config.exists():
                    raise FileNotFoundError(
                        f"OpenVoice V1 base speaker checkpoints not found at {v1_en_config.parent}"
                    )

                self._base_tts = BaseSpeakerTTS(str(v1_en_config), device=device)
                self._base_tts.load_ckpt(str(v1_en_ckpt))
                self._base_tts_type = "v1"

                # Load V1 base speaker SE embeddings for source tone color.
                v1_en_se = self._v1_dir / "checkpoints" / "base_speakers" / "EN" / "en_default_se.pth"
                if v1_en_se.exists():
                    self._base_speaker_se["en-default"] = torch.load(
                        v1_en_se, map_location=device, weights_only=True,
                    )

                logger.info(
                    "openvoice.base_tts",
                    type="BaseSpeakerTTS_v1",
                    note="Install melotts for full V2 multi-lingual support",
                )

            # Determine sample rate from the TTS model.
            if self._base_tts_type == "melo":
                self._sample_rate = getattr(
                    self._base_tts.hps.data, "sampling_rate", 22050
                )
            elif self._base_tts_type == "v1":
                self._sample_rate = getattr(
                    self._base_tts.hps.data, "sampling_rate", 22050
                )

            logger.info("openvoice.loaded", device=device, base_tts_type=self._base_tts_type)

        except Exception as exc:
            logger.error("openvoice.load_failed", error=str(exc))
            self._tone_converter = None
            self._base_tts = None
            raise

    def unload(self) -> None:
        self._tone_converter = None
        self._base_tts = None
        self._base_speaker_se.clear()
        self._cloned_voices.clear()
        try:
            import torch

            torch.cuda.empty_cache()
        except Exception:
            pass
        logger.info("openvoice.unloaded")

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        reference_audio: Path | None = None,
    ) -> tuple[np.ndarray, int]:
        self._ensure_loaded()

        import soundfile as sf

        try:
            # -------------------------------------------------------
            # Step 1: Generate base speech using the base TTS model.
            # -------------------------------------------------------
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                base_path = tmp.name

            if self._base_tts_type == "melo":
                speaker_ids = self._base_tts.hps.data.spk2id
                speaker_key = list(speaker_ids.keys())[0]
                speaker_id = speaker_ids[speaker_key]
                self._base_tts.tts_to_file(text, speaker_id, base_path, speed=speed)
            elif self._base_tts_type == "v1":
                self._base_tts.tts(
                    text, base_path, speaker="default", language="English", speed=speed,
                )
            else:
                raise RuntimeError("No base TTS model available")

            # -------------------------------------------------------
            # Step 2: If we have a cloned voice or reference audio,
            #         apply tone color conversion.
            # -------------------------------------------------------
            clone_info = self._cloned_voices.get(voice_id)
            tgt_se = None

            if clone_info and "se" in clone_info:
                tgt_se = clone_info["se"]
            elif reference_audio and reference_audio.exists():
                tgt_se = self._extract_se_from_audio(reference_audio)

            if tgt_se is not None:
                # Get source speaker embedding (the base TTS voice).
                src_se = self._get_source_se()

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    output_path = tmp.name

                self._tone_converter.convert(
                    audio_src_path=base_path,
                    src_se=src_se,
                    tgt_se=tgt_se,
                    output_path=output_path,
                )
                audio_array, sr = sf.read(output_path)

                # Clean up temp files.
                _safe_remove(output_path)
            else:
                # No voice cloning — return base speech directly.
                audio_array, sr = sf.read(base_path)

            # Clean up base temp file.
            _safe_remove(base_path)

            return np.asarray(audio_array, dtype=np.float32), int(sr)

        except Exception as exc:
            logger.error("openvoice.synthesize_failed", error=str(exc))
            raise

    # ------------------------------------------------------------------
    # Voice cloning
    # ------------------------------------------------------------------

    def clone_voice(self, samples: list[Path], name: str = "", language: str = "en") -> dict:
        self._ensure_loaded()
        if not samples:
            raise ValueError("At least one audio sample is required for cloning")

        voice_id = name or f"openvoice_clone_{len(self._cloned_voices)}"

        # Extract speaker embedding from the reference audio samples.
        se = self._extract_se_from_audio(samples[0])

        self._cloned_voices[voice_id] = {
            "voice_id": voice_id,
            "name": name or voice_id,
            "reference": str(samples[0]),
            "language": language,
            "provider": self.name,
            "se": se,  # torch tensor, not serialized
        }
        logger.info("openvoice.voice_cloned", voice_id=voice_id)

        # Return metadata without the SE tensor (not JSON-serializable).
        return {k: v for k, v in self._cloned_voices[voice_id].items() if k != "se"}

    # ------------------------------------------------------------------
    # Voices & capabilities
    # ------------------------------------------------------------------

    def list_voices(self) -> list[dict]:
        voices: list[dict] = [
            {
                "voice_id": "default",
                "name": "OpenVoice Default",
                "language": "en",
                "provider": self.name,
            }
        ]
        # Return cloned voices without the SE tensor.
        for v in self._cloned_voices.values():
            voices.append({k: val for k, val in v.items() if k != "se"})
        return voices

    def get_capabilities(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "installed": _OPENVOICE_AVAILABLE,
            "is_loaded": self.is_loaded,
            "supports_cloning": True,
            "supports_zero_shot": True,
            "supports_streaming": False,
            "supports_ssml": False,
            "requires_gpu": True,
            "vram_estimate_mb": self.vram_estimate_mb,
            "supported_languages": self._get_supported_languages(),
            "model": _HF_V2_REPO,
            "base_tts": self._base_tts_type if self._base_tts else "none",
            "note": (
                "Install melotts for full V2 multi-lingual support"
                if not _MELOTTS_AVAILABLE
                else ""
            ),
        }

    @property
    def is_loaded(self) -> bool:
        return self._tone_converter is not None and self._base_tts is not None

    @property
    def vram_estimate_mb(self) -> int:
        return 2000

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            raise RuntimeError(
                f"{self.display_name} model is not loaded. Call POST /providers/{self.name}/load first."
            )

    def _get_source_se(self) -> Any:
        """Return the source speaker embedding for the loaded base TTS voice."""
        import torch

        # Prefer the matching base speaker SE.
        for key in ("en-default", "en-us", "en"):
            if key in self._base_speaker_se:
                return self._base_speaker_se[key]

        # If no pre-computed SE exists, try the first available one.
        if self._base_speaker_se:
            return next(iter(self._base_speaker_se.values()))

        # Last resort: return zeros (will produce degraded output).
        logger.warning("openvoice.no_source_se", msg="No base speaker SE found, cloning quality will be degraded")
        return torch.zeros(1, 256, 1, device=self._device)

    def _extract_se_from_audio(self, audio_path: Path) -> Any:
        """Extract speaker embedding from a reference audio file."""
        # Use the ToneColorConverter's built-in SE extraction.
        se = self._tone_converter.extract_se(
            ref_wav_list=[str(audio_path)],
        )
        return se

    def _get_supported_languages(self) -> list[str]:
        """Return supported languages based on the active base TTS."""
        if self._base_tts_type == "melo":
            return ["en", "zh", "ja", "ko", "fr", "de", "es", "it", "pt"]
        elif self._base_tts_type == "v1":
            return ["en", "zh"]
        return ["en"]


def _safe_remove(path: str) -> None:
    """Remove a file, ignoring errors."""
    try:
        os.remove(path)
    except OSError:
        pass
