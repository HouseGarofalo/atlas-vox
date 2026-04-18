"""P0-01 regression: enforce capability-flag honesty across all providers.

Rules enforced:
1. If a provider advertises ``supports_cloning=True``, ``clone_voice()`` must
   not raise ``NotImplementedError`` (it may raise other errors when inputs are
   invalid — that's fine).
2. If ``supports_cloning=False``, ``clone_voice()`` MUST raise
   ``NotImplementedError`` (not silently return a fake ``VoiceModel``).
3. Mirror rules for ``supports_fine_tuning`` / ``fine_tune()``.

This guards against drift where capability flags stay True but the
implementation has been stubbed out, or where a stub silently succeeds.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.providers.base import (
    CloneConfig,
    FineTuneConfig,
    ProviderAudioSample,
)
from app.services.provider_registry import PROVIDER_CLASSES, provider_registry

CORE_PROVIDERS = [
    "kokoro",
    "coqui_xtts",
    "piper",
    "elevenlabs",
    "azure_speech",
    "styletts2",
    "cosyvoice",
    "dia",
    "dia2",
]


def _dummy_samples(count: int = 3, duration: float = 10.0) -> list[ProviderAudioSample]:
    """Build a list of dummy samples. Enough to pass common duration gates."""
    return [
        ProviderAudioSample(
            file_path=Path(f"/tmp/atlas-vox-test-sample-{i}.wav"),
            duration_seconds=duration,
            sample_rate=22050,
            transcript=f"sample {i}",
        )
        for i in range(count)
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("name", CORE_PROVIDERS)
async def test_clone_voice_matches_capability(name: str) -> None:
    if name not in PROVIDER_CLASSES:
        pytest.skip(f"Provider {name} not registered in this build")

    provider = provider_registry.get_provider(name)
    caps = await provider.get_capabilities()

    if caps.supports_cloning:
        # True cap → must not hit the NotImplementedError guard.
        try:
            await provider.clone_voice(_dummy_samples(3, 30.0), CloneConfig(name="x"))
        except NotImplementedError as exc:
            pytest.fail(
                f"{name}.clone_voice raised NotImplementedError despite "
                f"supports_cloning=True: {exc}"
            )
        except Exception:
            # Any other error (missing API key, missing audio, SDK call) is
            # acceptable — we only enforce the capability contract here.
            pass
    else:
        # False cap → must raise NotImplementedError (not silently succeed).
        with pytest.raises(NotImplementedError):
            await provider.clone_voice(_dummy_samples(3, 30.0), CloneConfig(name="x"))


@pytest.mark.asyncio
@pytest.mark.parametrize("name", CORE_PROVIDERS)
async def test_fine_tune_matches_capability(name: str) -> None:
    if name not in PROVIDER_CLASSES:
        pytest.skip(f"Provider {name} not registered in this build")

    provider = provider_registry.get_provider(name)
    caps = await provider.get_capabilities()

    if caps.supports_fine_tuning:
        try:
            await provider.fine_tune("model-x", _dummy_samples(3, 30.0), FineTuneConfig())
        except NotImplementedError as exc:
            pytest.fail(
                f"{name}.fine_tune raised NotImplementedError despite "
                f"supports_fine_tuning=True: {exc}"
            )
        except Exception:
            pass
    else:
        with pytest.raises(NotImplementedError):
            await provider.fine_tune("model-x", _dummy_samples(3, 30.0), FineTuneConfig())
