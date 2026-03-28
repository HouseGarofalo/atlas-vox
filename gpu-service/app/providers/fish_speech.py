"""Fish Speech GPU provider (OpenAudio S1 / Fish Speech 1.5).

Requires ``pip install fish-speech``.  When the package is not installed the
provider will still load but report ``installed: false`` in its capabilities.

The installed ``fish-speech`` pip package (v0.1.0) is the **OpenAudio S1** codebase.
It uses a two-stage pipeline:
  1. **Text-to-Semantic** — a DualAR transformer (LLaMA-like) that converts text
     into discrete VQ tokens.  Runs in a background thread via a queue.
  2. **DAC Decoder** — converts VQ tokens back to audio waveforms.

Model sources (tried in order):
  - ``fishaudio/openaudio-s1-mini`` — preferred, fully compatible with the pip
    package.  **Gated repo**: requires HuggingFace authentication and access
    approval at https://huggingface.co/fishaudio/openaudio-s1-mini.
  - ``fishaudio/fish-speech-1.5`` — public but uses an older Firefly GAN vocoder
    that is **not** compatible with the DAC decoder in the pip package.  When this
    model is detected the provider loads only the text-to-semantic model and
    requires a separate vocoder (not yet implemented).

On first ``load()`` the model snapshot is downloaded automatically via
``huggingface_hub.snapshot_download``.
"""

from __future__ import annotations

import queue
from pathlib import Path
from typing import Any

import numpy as np
import structlog

from app.providers.base import GPUProviderBase

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Gate import so the provider is importable even when the library is absent.
# ---------------------------------------------------------------------------
try:
    import fish_speech  # noqa: F401

    _FISH_SPEECH_AVAILABLE = True
except ImportError:
    _FISH_SPEECH_AVAILABLE = False


# Model repos and local cache directories.
_PREFERRED_REPO = "fishaudio/openaudio-s1-mini"
_FALLBACK_REPO = "fishaudio/fish-speech-1.5"
_DEFAULT_MODEL_DIR = Path("storage/models/fish-speech")


def _load_dac_model(checkpoint_path: str, device: str = "cuda") -> Any:
    """Load the DAC decoder model using Hydra config.

    Re-implements ``fish_speech.models.dac.inference.load_model`` without the
    ``pyrootutils.setup_root`` call that fails outside the original Fish Speech
    project tree.
    """
    import torch
    from hydra import compose, initialize_config_dir
    from hydra.utils import instantiate
    from omegaconf import OmegaConf
    import hydra as _hydra

    try:
        OmegaConf.register_new_resolver("eval", eval)
    except ValueError:
        pass

    config_dir = str(Path(fish_speech.__path__[0]) / "configs")

    _hydra.core.global_hydra.GlobalHydra.instance().clear()
    with initialize_config_dir(version_base="1.3", config_dir=config_dir):
        cfg = compose(config_name="modded_dac_vq")

    model = instantiate(cfg)
    state_dict = torch.load(
        checkpoint_path, map_location=device, mmap=True, weights_only=True
    )
    if "state_dict" in state_dict:
        state_dict = state_dict["state_dict"]

    if any("generator" in k for k in state_dict):
        state_dict = {
            k.replace("generator.", ""): v
            for k, v in state_dict.items()
            if "generator." in k
        }

    model.load_state_dict(state_dict, strict=False, assign=True)
    model.eval()
    model.to(device)
    return model


class FishSpeechProvider(GPUProviderBase):
    """Fish Speech — multilingual TTS with zero-shot voice cloning.

    Model: ``fishaudio/openaudio-s1-mini`` (preferred) or
    ``fishaudio/fish-speech-1.5`` (fallback, limited).
    """

    name = "fish_speech"
    display_name = "Fish Speech"

    def __init__(self) -> None:
        self._engine: Any = None  # TTSInferenceEngine
        self._llama_queue: queue.Queue | None = None
        self._device: str = "cuda:0"
        self._model_dir: Path = _DEFAULT_MODEL_DIR
        self._model_repo: str = ""
        self._sample_rate: int = 44100
        self._cloned_voices: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self, device: str = "cuda:0") -> None:
        if not _FISH_SPEECH_AVAILABLE:
            raise RuntimeError("fish-speech is not installed. Run: pip install fish-speech")

        self._device = device
        logger.info("fish_speech.loading", device=device)

        try:
            import torch
            from huggingface_hub import snapshot_download

            from fish_speech.inference_engine import TTSInferenceEngine
            from fish_speech.models.text2semantic.inference import launch_thread_safe_queue

            # ----------------------------------------------------------
            # Step 1: Download model snapshot (try preferred, then fallback).
            # ----------------------------------------------------------
            model_dir: Path | None = None
            active_repo = ""

            for repo_id in (_PREFERRED_REPO, _FALLBACK_REPO):
                try:
                    local_dir = _DEFAULT_MODEL_DIR / repo_id.split("/")[-1]
                    model_dir = Path(
                        snapshot_download(repo_id, local_dir=str(local_dir))
                    )
                    active_repo = repo_id
                    logger.info("fish_speech.model_downloaded", repo=repo_id, path=str(model_dir))
                    break
                except Exception as dl_err:
                    logger.warning(
                        "fish_speech.download_skipped",
                        repo=repo_id,
                        reason=str(dl_err),
                    )
                    continue

            if model_dir is None:
                raise RuntimeError(
                    "Could not download any Fish Speech model. "
                    f"Tried: {_PREFERRED_REPO} (gated, requires auth), {_FALLBACK_REPO}. "
                    "Please authenticate with `huggingface-cli login` and request access "
                    f"to {_PREFERRED_REPO}."
                )

            self._model_dir = model_dir
            self._model_repo = active_repo

            # ----------------------------------------------------------
            # Step 2: Check for the DAC codec checkpoint.
            # ----------------------------------------------------------
            codec_ckpt = model_dir / "codec.pth"
            if not codec_ckpt.exists():
                # Fish Speech 1.5 has firefly-gan-vq which is incompatible
                # with the installed pip package's DAC decoder.
                firefly = list(model_dir.glob("firefly-*.pth"))
                if firefly:
                    raise RuntimeError(
                        f"The downloaded model ({active_repo}) uses a Firefly GAN VQ "
                        "vocoder which is incompatible with the installed fish-speech "
                        "pip package (OpenAudio S1 / DAC decoder). Please authenticate "
                        f"with HuggingFace and request access to {_PREFERRED_REPO} "
                        "for a compatible model, or install the matching fish-speech "
                        "version for this model."
                    )
                raise FileNotFoundError(
                    f"codec.pth not found in {model_dir}. Model snapshot may be incomplete."
                )

            # ----------------------------------------------------------
            # Step 3: Determine precision.
            # ----------------------------------------------------------
            precision = torch.bfloat16 if "cuda" in device else torch.float32

            # ----------------------------------------------------------
            # Step 4: Launch the LLaMA text-to-semantic worker thread.
            # ----------------------------------------------------------
            self._llama_queue = launch_thread_safe_queue(
                checkpoint_path=str(model_dir),
                device=device,
                precision=precision,
                compile=False,
            )

            # ----------------------------------------------------------
            # Step 5: Load the DAC decoder model.
            # ----------------------------------------------------------
            decoder_model = _load_dac_model(
                checkpoint_path=str(codec_ckpt),
                device=device,
            )

            # ----------------------------------------------------------
            # Step 6: Assemble the TTSInferenceEngine.
            # ----------------------------------------------------------
            self._engine = TTSInferenceEngine(
                llama_queue=self._llama_queue,
                decoder_model=decoder_model,
                precision=precision,
                compile=False,
            )

            # Discover actual sample rate from the decoder.
            if hasattr(decoder_model, "spec_transform"):
                self._sample_rate = decoder_model.spec_transform.sample_rate
            elif hasattr(decoder_model, "sample_rate"):
                self._sample_rate = decoder_model.sample_rate

            logger.info(
                "fish_speech.loaded",
                device=device,
                repo=active_repo,
                sample_rate=self._sample_rate,
            )

        except Exception as exc:
            logger.error("fish_speech.load_failed", error=str(exc))
            self._engine = None
            self._llama_queue = None
            raise

    def unload(self) -> None:
        # Signal the LLaMA worker thread to exit.
        if self._llama_queue is not None:
            try:
                self._llama_queue.put(None)
            except Exception:
                pass
            self._llama_queue = None

        if self._engine is not None:
            del self._engine
            self._engine = None

        try:
            import torch

            torch.cuda.empty_cache()
        except Exception:
            pass

        logger.info("fish_speech.unloaded")

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

        from fish_speech.utils.file import audio_to_bytes
        from fish_speech.utils.schema import ServeReferenceAudio, ServeTTSRequest

        # Build reference list for zero-shot cloning.
        references: list[ServeReferenceAudio] = []
        ref_path = reference_audio

        if voice_id in self._cloned_voices:
            clone_info = self._cloned_voices[voice_id]
            ref_path = ref_path or Path(clone_info.get("reference", ""))
            ref_text = clone_info.get("reference_text", "")
        else:
            ref_text = ""

        if ref_path and ref_path.exists():
            audio_bytes = audio_to_bytes(str(ref_path))
            if audio_bytes:
                references.append(
                    ServeReferenceAudio(audio=audio_bytes, text=ref_text)
                )

        # Build the TTS request.
        request = ServeTTSRequest(
            text=text,
            references=references,
            streaming=False,
            normalize=True,
        )

        try:
            final_audio: np.ndarray | None = None
            final_sr: int = self._sample_rate

            for result in self._engine.inference(request):
                if result.code == "error":
                    raise result.error or RuntimeError("Fish Speech inference error")
                if result.code == "final" and result.audio is not None:
                    final_sr, final_audio = result.audio

            if final_audio is None:
                raise RuntimeError("Fish Speech produced no audio output.")

            return np.asarray(final_audio, dtype=np.float32), int(final_sr)

        except Exception as exc:
            logger.error("fish_speech.synthesize_failed", error=str(exc))
            raise

    # ------------------------------------------------------------------
    # Voice cloning
    # ------------------------------------------------------------------

    def clone_voice(self, samples: list[Path], name: str = "", language: str = "en") -> dict:
        self._ensure_loaded()
        if not samples:
            raise ValueError("At least one audio sample is required for cloning")

        voice_id = name or f"fish_clone_{len(self._cloned_voices)}"
        self._cloned_voices[voice_id] = {
            "voice_id": voice_id,
            "name": name or voice_id,
            "reference": str(samples[0]),
            "reference_text": "",
            "language": language,
            "provider": self.name,
        }
        logger.info("fish_speech.voice_cloned", voice_id=voice_id)
        return self._cloned_voices[voice_id]

    # ------------------------------------------------------------------
    # Voices & capabilities
    # ------------------------------------------------------------------

    def list_voices(self) -> list[dict]:
        voices: list[dict] = [
            {
                "voice_id": "default",
                "name": "Fish Speech Default",
                "language": "en",
                "provider": self.name,
            }
        ]
        voices.extend(self._cloned_voices.values())
        return voices

    def get_capabilities(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "installed": _FISH_SPEECH_AVAILABLE,
            "is_loaded": self.is_loaded,
            "supports_cloning": True,
            "supports_zero_shot": True,
            "supports_streaming": False,
            "supports_ssml": False,
            "requires_gpu": True,
            "vram_estimate_mb": self.vram_estimate_mb,
            "supported_languages": ["en", "zh", "ja", "ko", "fr", "de", "es"],
            "model": self._model_repo or _PREFERRED_REPO,
        }

    @property
    def is_loaded(self) -> bool:
        return self._engine is not None

    @property
    def vram_estimate_mb(self) -> int:
        return 4000

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            raise RuntimeError(
                f"{self.display_name} model is not loaded. Call POST /providers/{self.name}/load first."
            )
