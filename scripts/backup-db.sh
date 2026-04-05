#!/usr/bin/env bash
# Atlas Vox — Database backup script
# Copies the SQLite database from the Docker volume to a timestamped backup file.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[backup]${NC} $1"; }
warn() { echo -e "${YELLOW}[backup]${NC} $1"; }
err()  { echo -e "${RED}[backup]${NC} $1"; }

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/atlas_vox_${TIMESTAMP}.db"

mkdir -p "$BACKUP_DIR"

# Check if Docker container is running
if docker ps --filter "name=atlas-vox-backend" --format "{{.Names}}" 2>/dev/null | grep -q atlas-vox-backend; then
    log "Backing up from Docker container..."
    docker cp atlas-vox-backend:/app/data/atlas_vox.db "$BACKUP_FILE" 2>/dev/null
    if [ $? -eq 0 ]; then
        SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log "Backup created: $BACKUP_FILE ($SIZE)"
    else
        err "Failed to copy database from Docker container"
        exit 1
    fi
elif [ -f "$PROJECT_ROOT/backend/atlas_vox.db" ]; then
    log "Backing up local database..."
    cp "$PROJECT_ROOT/backend/atlas_vox.db" "$BACKUP_FILE"
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup created: $BACKUP_FILE ($SIZE)"
else
    err "No database found to backup"
    exit 1
fi

# Clean up old backups (keep last 10)
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/atlas_vox_*.db 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 10 ]; then
    REMOVE_COUNT=$((BACKUP_COUNT - 10))
    log "Cleaning up $REMOVE_COUNT old backups (keeping 10)..."
    ls -1t "$BACKUP_DIR"/atlas_vox_*.db | tail -n "$REMOVE_COUNT" | xargs rm -f
fi

log "Done. Total backups: $(ls -1 "$BACKUP_DIR"/atlas_vox_*.db 2>/dev/null | wc -l)"
