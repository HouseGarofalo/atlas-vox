#!/bin/bash
# =============================================================================
# Atlas Vox — Model Initialization Script
# =============================================================================
# Runs at container startup. Downloads models if not present in the persistent
# storage volume, then restores them to the HuggingFace cache.
# =============================================================================

set -e

echo "[init-models] Starting model initialization..."

# ---------------------------------------------------------------------------
# Piper TTS model (ONNX, ~30MB)
# ---------------------------------------------------------------------------

PIPER_DIR="/app/storage/models/piper"
mkdir -p "$PIPER_DIR"

if [ ! -f "$PIPER_DIR/en_US-lessac-medium.onnx" ]; then
    echo "[init-models] Downloading Piper model..."
    python3 /tmp/download_piper_model.py 2>/dev/null && \
        echo "[init-models] Piper model downloaded." || \
        echo "[init-models] Piper download failed (offline?)."
    # Also try the image-baked copy
    if [ -f "/app/storage_bak/models/piper/en_US-lessac-medium.onnx" ]; then
        cp /app/storage_bak/models/piper/* "$PIPER_DIR/" 2>/dev/null || true
    fi
else
    echo "[init-models] Piper model present."
fi

# ---------------------------------------------------------------------------
# Kokoro TTS model (313 MB .pth + config + voice files)
# ---------------------------------------------------------------------------

KOKORO_STORAGE="/app/storage/models/kokoro"
mkdir -p "$KOKORO_STORAGE/voices"

# Download Kokoro to storage volume if not present
if [ ! -f "$KOKORO_STORAGE/kokoro-v1_0.pth" ]; then
    echo "[init-models] Downloading Kokoro model (this may take a few minutes)..."
    python3 -c "
import os, urllib.request, time

base = 'https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/'
dest_dir = '$KOKORO_STORAGE'

files = [
    ('kokoro-v1_0.pth', os.path.join(dest_dir, 'kokoro-v1_0.pth')),
    ('config.json', os.path.join(dest_dir, 'config.json')),
]
voices = ['af_heart', 'af_bella', 'af_nicole', 'af_sarah', 'af_sky', 'af_alloy',
          'am_adam', 'am_michael', 'am_echo',
          'bf_emma', 'bf_alice', 'bm_george', 'bm_lewis', 'bm_daniel']
files += [(f'voices/{v}.pt', os.path.join(dest_dir, f'voices/{v}.pt')) for v in voices]

for url_path, dest in files:
    if os.path.exists(dest):
        continue
    for attempt in range(3):
        try:
            urllib.request.urlretrieve(base + url_path, dest)
            print(f'  Downloaded {url_path}')
            break
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
            else:
                print(f'  WARNING: Failed {url_path}: {e}')
print('Kokoro download complete')
" 2>&1 || echo "[init-models] Kokoro download failed (offline?)."
else
    echo "[init-models] Kokoro model present in storage."
fi

# Restore Kokoro from storage to HuggingFace cache
# Try multiple possible snapshot hashes
for SNAPSHOT_DIR in /root/.cache/huggingface/hub/models--hexgrad--Kokoro-82M/snapshots/*/; do
    if [ -d "$SNAPSHOT_DIR" ] && [ -f "$SNAPSHOT_DIR/kokoro-v1_0.pth" ]; then
        echo "[init-models] Kokoro already in HF cache."
        break
    fi
done

# If no cache exists, create one from storage
if [ -f "$KOKORO_STORAGE/kokoro-v1_0.pth" ]; then
    KOKORO_CACHE="/root/.cache/huggingface/hub/models--hexgrad--Kokoro-82M/snapshots/main"
    if [ ! -f "$KOKORO_CACHE/kokoro-v1_0.pth" ]; then
        echo "[init-models] Restoring Kokoro to HF cache..."
        mkdir -p "$KOKORO_CACHE/voices"
        cp "$KOKORO_STORAGE/kokoro-v1_0.pth" "$KOKORO_CACHE/"
        cp "$KOKORO_STORAGE/config.json" "$KOKORO_CACHE/" 2>/dev/null || true
        if [ -d "$KOKORO_STORAGE/voices" ]; then
            cp "$KOKORO_STORAGE/voices/"*.pt "$KOKORO_CACHE/voices/" 2>/dev/null || true
        fi
        echo "[init-models] Kokoro restored ($(du -sh "$KOKORO_CACHE" | cut -f1))"
    fi
fi

# ---------------------------------------------------------------------------
# Fix numpy ABI if needed
# ---------------------------------------------------------------------------

python3 -c "import numpy; v = tuple(map(int, numpy.__version__.split('.')[:2])); assert v >= (2, 0)" 2>/dev/null || {
    echo "[init-models] Fixing numpy ABI..."
    pip install --quiet --no-cache-dir --force-reinstall "numpy>=2.0,<3.0" "pandas>=2.2"
}

# ---------------------------------------------------------------------------
# Database migrations
# ---------------------------------------------------------------------------

if [ -f "/app/alembic.ini" ]; then
    echo "[init-models] Running database migrations..."
    python3 -m alembic upgrade head 2>/dev/null || true
fi

echo "[init-models] Initialization complete."
