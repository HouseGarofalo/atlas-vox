#!/bin/bash
# Atlas Vox — Container entrypoint
# Fixes volume permissions (as root), then drops to the 'app' user.

set -e

# Fix ownership of mounted volumes (created as root by Docker)
chown -R app:app /app/storage /app/data 2>/dev/null || true
chown -R app:app /home/app 2>/dev/null || true

# Run init-models.sh as root (needs write access everywhere for model downloads)
export HOME=/home/app
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
