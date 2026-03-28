#!/bin/bash
# =============================================================================
# Atlas Vox — Model Initialization Script
# =============================================================================
# Runs inside the backend container on startup. Copies pre-downloaded models
# from the persistent storage volume to the HuggingFace cache directory so
# they survive container rebuilds.
#
# The storage volume (/app/storage) is Docker-managed and persists across
# restarts. The HuggingFace cache (/root/.cache/huggingface/) lives in the
# container's filesystem and is rebuilt from the image each time.
#
# This script is idempotent — safe to run multiple times.
# =============================================================================

set -e

# ---------------------------------------------------------------------------
# Kokoro TTS model (313 MB .pth + config + 28 voice files)
# ---------------------------------------------------------------------------

KOKORO_SNAPSHOT="f3ff3571791e39611d31c381e3a41a3af07b4987"
KOKORO_CACHE="/root/.cache/huggingface/hub/models--hexgrad--Kokoro-82M/snapshots/${KOKORO_SNAPSHOT}"
KOKORO_STORAGE="/app/storage/models/kokoro"

if [ -d "$KOKORO_STORAGE" ] && [ -f "$KOKORO_STORAGE/kokoro-v1_0.pth" ]; then
    if [ ! -f "$KOKORO_CACHE/kokoro-v1_0.pth" ]; then
        echo "[init-models] Copying Kokoro model from storage to HuggingFace cache..."
        mkdir -p "$KOKORO_CACHE/voices"
        cp "$KOKORO_STORAGE/kokoro-v1_0.pth" "$KOKORO_CACHE/"
        cp "$KOKORO_STORAGE/config.json" "$KOKORO_CACHE/" 2>/dev/null || true

        # Copy all voice files
        if [ -d "$KOKORO_STORAGE/voices" ]; then
            cp "$KOKORO_STORAGE/voices/"*.pt "$KOKORO_CACHE/voices/" 2>/dev/null || true
        fi

        echo "[init-models] Kokoro model restored ($(du -sh "$KOKORO_CACHE" | cut -f1))"
    else
        echo "[init-models] Kokoro model already in cache, skipping."
    fi
else
    echo "[init-models] No Kokoro model in storage — will download on first use."
fi

# ---------------------------------------------------------------------------
# Piper TTS model (ONNX)
# ---------------------------------------------------------------------------

PIPER_CACHE="/app/storage/models/piper"

if [ -d "$PIPER_CACHE" ] && [ -f "$PIPER_CACHE/en_US-lessac-medium.onnx" ]; then
    echo "[init-models] Piper model present in storage."
else
    echo "[init-models] No Piper model in storage — using image-baked model if available."
fi

# ---------------------------------------------------------------------------
# Fix numpy ABI if needed (transitive deps can downgrade numpy)
# ---------------------------------------------------------------------------

python3 -c "import numpy; v = tuple(map(int, numpy.__version__.split('.')[:2])); assert v >= (2, 0)" 2>/dev/null || {
    echo "[init-models] Fixing numpy ABI (upgrading to numpy 2.x)..."
    pip install --quiet --no-cache-dir --force-reinstall "numpy>=2.0,<3.0" "pandas>=2.2"
    echo "[init-models] numpy fixed: $(python3 -c 'import numpy; print(numpy.__version__)')"
}

echo "[init-models] Model initialization complete."
