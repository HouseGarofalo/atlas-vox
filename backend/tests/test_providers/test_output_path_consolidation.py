"""P2-19 — every provider funnels synthesis output through ``prepare_output_path``.

Regression guard: if somebody sneaks in a hand-rolled ``Path(settings.storage_path)``
synthesis output path in a future provider change, this test flags it before
review instead of after merge.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROVIDERS_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "providers"

# Providers exempted because the manual path is for *model weights* cached on
# disk, not synthesis *output* files.
_MODEL_WEIGHT_PROVIDERS = {"coqui_xtts.py", "styletts2.py", "piper_tts.py"}


def _iter_provider_files():
    for p in sorted(PROVIDERS_DIR.glob("*.py")):
        if p.name.startswith("__"):
            continue
        yield p


def test_prepare_output_path_is_the_only_synthesis_output_writer():
    """Any file writing to storage_path/output/* must route via prepare_output_path.

    We look for string literals like ``"/output"`` or ``Path(settings.storage_path) / "output"``
    in provider files and assert they only occur in ``base.py`` (the one true
    implementation) and ``audio_processor`` / ``remote_provider`` style files
    that do not belong to the TTS provider surface.
    """
    offending: list[str] = []
    pattern = re.compile(
        r'(settings\.storage_path[^"]*"output"|storage_path\s*\)\s*/\s*"output")',
    )
    for file in _iter_provider_files():
        if file.name == "base.py":
            continue
        src = file.read_text(encoding="utf-8")
        # Model-weight caches for local providers use storage_path/models/*,
        # never storage_path/output/*, so we only flag the literal "output".
        if pattern.search(src):
            offending.append(file.name)
    assert not offending, (
        "Providers still constructing synthesis output paths manually: "
        + ", ".join(offending)
        + ". Use TTSProvider.prepare_output_path(...) instead."
    )


@pytest.mark.parametrize("provider_file", [p.name for p in _iter_provider_files()])
def test_every_provider_that_writes_audio_uses_prepare_output_path(provider_file):
    """Smoke check — if a provider implements ``synthesize``, it must call
    ``prepare_output_path`` (or delegate, like remote_provider).
    """
    file = PROVIDERS_DIR / provider_file
    src = file.read_text(encoding="utf-8")
    # Skip the base class + files that don't define a provider.
    if provider_file in {"base.py", "__init__.py", "registry.py"}:
        pytest.skip("non-provider module")
    # Providers that *don't* define synthesize() get a free pass too.
    if "async def synthesize" not in src:
        pytest.skip("no synthesize() in this module")
    assert "prepare_output_path" in src, (
        f"{provider_file} has synthesize() but does not call "
        "prepare_output_path() — use the base-class helper."
    )
