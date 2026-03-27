"""GPU resource manager — reports CUDA device status and assigns devices to providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class DeviceInfo:
    """Snapshot of a single CUDA device."""

    index: int
    name: str
    total_vram_mb: int
    used_vram_mb: int
    free_vram_mb: int


class GPUManager:
    """Singleton-style manager for GPU resources."""

    def __init__(self) -> None:
        self._torch_available = False
        try:
            import torch  # noqa: F401

            self._torch_available = True
        except ImportError:
            logger.warning("torch_not_found", msg="PyTorch is not installed — GPU features disabled")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_devices(self) -> list[DeviceInfo]:
        """Return a list of CUDA devices with VRAM statistics."""
        if not self._torch_available:
            return []

        import torch

        if not torch.cuda.is_available():
            return []

        devices: list[DeviceInfo] = []
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            total_mb = props.total_mem // (1024 * 1024)
            reserved = torch.cuda.memory_reserved(i) // (1024 * 1024)
            allocated = torch.cuda.memory_allocated(i) // (1024 * 1024)
            used_mb = max(reserved, allocated)
            devices.append(
                DeviceInfo(
                    index=i,
                    name=props.name,
                    total_vram_mb=total_mb,
                    used_vram_mb=used_mb,
                    free_vram_mb=total_mb - used_mb,
                )
            )
        return devices

    def get_device_for_provider(self, name: str) -> str:
        """Return the CUDA device string for *name*, consulting ``device_map`` first."""
        return settings.device_map.get(name, settings.default_device)

    def get_status(self) -> dict[str, Any]:
        """Return a full GPU status dictionary suitable for JSON serialization."""
        devices = self.get_devices()
        return {
            "torch_available": self._torch_available,
            "cuda_available": self._cuda_available,
            "device_count": len(devices),
            "devices": [
                {
                    "index": d.index,
                    "name": d.name,
                    "total_vram_mb": d.total_vram_mb,
                    "used_vram_mb": d.used_vram_mb,
                    "free_vram_mb": d.free_vram_mb,
                }
                for d in devices
            ],
            "default_device": settings.default_device,
            "device_map": settings.device_map,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @property
    def _cuda_available(self) -> bool:
        if not self._torch_available:
            return False
        import torch

        return torch.cuda.is_available()


# Module-level singleton
gpu_manager = GPUManager()
