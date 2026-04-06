#!/bin/bash
# Atlas Vox — Container entrypoint
# Fixes volume permissions (as root), then drops to the 'app' user.

set -e

# Fix ownership of mounted volumes (created as root by Docker)
chown -R app:app /app/storage /app/data 2>/dev/null || true

# Run init-models.sh as root (needs write access to /root/.cache for HF models)
/app/init-models.sh

# Drop privileges and exec the main command as 'app' user
exec gosu app "$@"
