"""Piper training GPU provider.

Uses ``piper-train`` to fine-tune existing Piper TTS models on user-supplied
audio samples and transcripts.  The output is an ONNX model compatible with the
lightweight Piper runtime already integrated into Atlas Vox's main backend.

This provider does **not** perform real-time synthesis — it runs training jobs.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import structlog

from app.providers.base import GPUProviderBase

logger = structlog.get_logger(__name__)

try:
    import piper_train  # type: ignore[import-untyped]  # noqa: F401

    _PIPER_TRAIN_AVAILABLE = True
except ImportError:
    _PIPER_TRAIN_AVAILABLE = False


class PiperTrainingProvider(GPUProviderBase):
    """Piper fine-tuning — train custom ONNX voices from audio samples."""

    name = "piper_training"
    display_name = "Piper Training"

    def __init__(self) -> None:
        self._loaded: bool = False
        self._device: str = "cuda:0"
        self._active_jobs: dict[str, dict] = {}
        self._trained_models: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self, device: str = "cuda:0") -> None:
        if not _PIPER_TRAIN_AVAILABLE:
            raise RuntimeError("piper-train is not installed. See: https://github.com/rhasspy/piper")
        self._device = device
        # Piper training doesn't hold a persistent model in VRAM — it loads
        # during training runs only.  We just mark ourselves as ready.
        self._loaded = True
        logger.info("piper_training.ready", device=device)

    def unload(self) -> None:
        self._loaded = False
        try:
            import torch

            torch.cuda.empty_cache()
        except Exception:
            pass
        logger.info("piper_training.unloaded")

    # ------------------------------------------------------------------
    # Synthesis (not supported — this is a training-only provider)
    # ------------------------------------------------------------------

    def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        reference_audio: Path | None = None,
    ) -> tuple[np.ndarray, int]:
        raise NotImplementedError(
            "PiperTrainingProvider does not perform synthesis. "
            "Use the trained ONNX model with the main Piper provider instead."
        )

    # ------------------------------------------------------------------
    # Voice cloning / training
    # ------------------------------------------------------------------

    def clone_voice(self, samples: list[Path], name: str = "", language: str = "en") -> dict:
        """Start a Piper fine-tuning job.

        *samples* should be a list of WAV files.  Transcripts are expected as
        sidecar ``.txt`` files (same stem, e.g. ``001.wav`` + ``001.txt``).
        """
        self._ensure_loaded()
        if not samples:
            raise ValueError("At least one audio sample with a matching .txt transcript is required")

        voice_id = name or f"piper_trained_{len(self._trained_models)}"
        dataset = self._prepare_dataset(samples)

        logger.info("piper_training.starting", voice_id=voice_id, num_samples=len(samples))

        job_info: dict[str, Any] = {
            "voice_id": voice_id,
            "name": name or voice_id,
            "language": language,
            "provider": self.name,
            "status": "queued",
            "dataset_path": str(dataset),
            "num_samples": len(samples),
        }
        self._active_jobs[voice_id] = job_info
        # In a real deployment, this would kick off an async training run.
        # For now we record the job metadata.
        return job_info

    # ------------------------------------------------------------------
    # Voices & capabilities
    # ------------------------------------------------------------------

    def list_voices(self) -> list[dict]:
        return list(self._trained_models.values())

    def get_capabilities(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "installed": _PIPER_TRAIN_AVAILABLE,
            "is_loaded": self.is_loaded,
            "supports_cloning": False,
            "supports_fine_tuning": True,
            "supports_zero_shot": False,
            "supports_streaming": False,
            "supports_ssml": False,
            "requires_gpu": True,
            "vram_estimate_mb": self.vram_estimate_mb,
            "supported_languages": ["en", "de", "fr", "es", "it", "pt", "pl", "nl", "ru", "uk"],
            "output_format": "onnx",
            "notes": "Training-only provider. Outputs ONNX models for the Piper runtime.",
        }

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def vram_estimate_mb(self) -> int:
        return 2000

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            raise RuntimeError(
                f"{self.display_name} is not loaded. Call POST /providers/{self.name}/load first."
            )

    @staticmethod
    def _prepare_dataset(samples: list[Path]) -> Path:
        """Organise samples into the directory layout piper-train expects.

        Returns the dataset root directory.
        """
        dataset_dir = samples[0].parent / "piper_dataset"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        wav_dir = dataset_dir / "wav"
        wav_dir.mkdir(exist_ok=True)

        metadata_lines: list[str] = []
        for sample in samples:
            dest = wav_dir / sample.name
            if not dest.exists():
                shutil.copy2(sample, dest)
            transcript_file = sample.with_suffix(".txt")
            transcript = ""
            if transcript_file.exists():
                transcript = transcript_file.read_text(encoding="utf-8").strip()
            metadata_lines.append(f"{sample.stem}|{transcript}")

        metadata_path = dataset_dir / "metadata.csv"
        metadata_path.write_text("\n".join(metadata_lines), encoding="utf-8")
        return dataset_dir
