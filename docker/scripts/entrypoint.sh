#!/bin/bash
# Atlas Vox — Container entrypoint
# Fixes volume permissions (as root), then drops to the 'app' user.

set -e

# Fix ownership of mounted volumes (created as root by Docker)
chown -R app:app /app/storage /app/data 2>/dev/null || true
chown -R app:app /home/app 2>/dev/null || true
# Celery beat schedule directory (used by celery-beat service)
mkdir -p /var/run/celery 2>/dev/null || true
chown -R app:app /var/run/celery 2>/dev/null || true

export HOME=/home/app

# If host models are mounted, copy them to the HF cache
if [ -f /app/models-host/kokoro-v1_0.pth ]; then
    HASH="f3ff3571791e39611d31c381e3a41a3af07b4987"
    CACHE="$HOME/.cache/huggingface/hub/models--hexgrad--Kokoro-82M"
    if [ ! -f "$CACHE/snapshots/$HASH/kokoro-v1_0.pth" ]; then
        echo "[entrypoint] Copying Kokoro model from host mount..."
        mkdir -p "$CACHE/snapshots/$HASH/voices" "$CACHE/refs"
        echo "$HASH" > "$CACHE/refs/main"
        cp /app/models-host/kokoro-v1_0.pth "$CACHE/snapshots/$HASH/"
        cp /app/models-host/config.json "$CACHE/snapshots/$HASH/" 2>/dev/null || true
        if [ -d /app/models-host/voices ]; then
            cp /app/models-host/voices/*.pt "$CACHE/snapshots/$HASH/voices/" 2>/dev/null || true
        fi
        chown -R app:app "$CACHE"
        echo "[entrypoint] Kokoro model ready from host mount."
    fi
fi

# Run init-models.sh (downloads anything still missing)
/app/init-models.sh

# Copy any baked models from the image to the storage volume
if [ -d /app/storage_bak/models ] && [ ! -f /app/storage/models/piper/en_US-lessac-medium.onnx ]; then
    echo "[entrypoint] Restoring baked models to storage volume..."
    cp -rn /app/storage_bak/models/* /app/storage/models/ 2>/dev/null || true
fi

# Fix ownership again after model downloads
chown -R app:app /app/storage /app/data /home/app 2>/dev/null || true

# Drop privileges and exec the main command as 'app' user
exec gosu app "$@"
