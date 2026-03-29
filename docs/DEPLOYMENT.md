# 🚀 Atlas Vox Deployment Guide

> Complete guide for deploying Atlas Vox in development, staging, and production environments.

---

## Table of Contents

- [Docker Compose Deployment](#-docker-compose-deployment)
- [GPU Deployment](#-gpu-deployment)
- [Environment Variables Reference](#-environment-variables-reference)
- [Port Configuration](#-port-configuration)
- [Volume Management](#-volume-management)
- [Reverse Proxy Setup](#-reverse-proxy-setup)
- [Production Hardening](#-production-hardening)
- [Backup and Restore](#-backup-and-restore)
- [Monitoring and Logging](#-monitoring-and-logging)
- [Scaling Considerations](#-scaling-considerations)

---

## 🐳 Docker Compose Deployment

Atlas Vox ships with production-ready Docker Compose configurations.

### Architecture

```
docker-compose.yml
├── backend       (FastAPI on :8100, Python 3.11)
├── frontend      (Nginx serving React build on :80)
├── redis         (Redis 7 Alpine on :6379)
└── worker        (Celery worker, same image as backend)

docker-compose.gpu.yml (extends above)
└── gpu-worker    (CUDA 12.1, NVIDIA GPU passthrough)
```

### Standard Deployment (CPU)

```bash
# Start all services
make docker-up

# Or equivalently:
docker compose -f docker/docker-compose.yml up --build

# Detached mode (background)
docker compose -f docker/docker-compose.yml up --build -d

# Stop all services
make docker-down
```

### Services Overview

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `backend` | `python:3.11-slim` | 8000 (internal) → 8100 (host) | FastAPI API server |
| `frontend` | `nginx:alpine` | 80 (internal) → 3100 (host) | Serves React build |
| `redis` | `redis:7-alpine` | 6379 (internal only) | Celery broker + cache |
| `worker` | Same as backend | None | Celery background tasks |

### Build Stages

The backend uses a multi-stage Docker build:

**Stage 1: Builder**
- Installs Python dependencies
- Installs CPU providers (Kokoro, Piper, ElevenLabs SDK, Azure SDK)
- Installs optional providers (Coqui TTS, StyleTTS2)
- Fixes numpy/pandas ABI compatibility

**Stage 2: Runtime**
- Installs system packages: `espeak-ng`, `ffmpeg`
- Copies built Python packages from builder
- Downloads default Piper model
- Downloads NLTK data for StyleTTS2

---

## 🖥️ GPU Deployment

For GPU-accelerated training and synthesis with local models.

### Prerequisites

1. **NVIDIA GPU** with 6 GB+ VRAM
2. **NVIDIA Driver** 525+
3. **NVIDIA Container Toolkit** installed:
   ```bash
   # Ubuntu
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt-get update
   sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

### Starting GPU Services

```bash
make docker-gpu-up

# Or equivalently:
docker compose -f docker/docker-compose.yml -f docker/docker-compose.gpu.yml up --build
```

This starts all standard services plus a `gpu-worker` with:
- CUDA 12.1 runtime
- PyTorch with CUDA support
- Automatic GPU passthrough via `nvidia` driver
- GPU mode pre-configured for all configurable providers

### GPU Worker Configuration

The GPU worker automatically sets these environment variables:

```bash
COQUI_XTTS_GPU_MODE=docker_gpu
STYLETTS2_GPU_MODE=docker_gpu
COSYVOICE_GPU_MODE=docker_gpu
DIA_GPU_MODE=docker_gpu
DIA2_GPU_MODE=docker_gpu
```

### Verifying GPU Access

```bash
# Check if GPU is visible inside the container
docker compose -f docker/docker-compose.yml -f docker/docker-compose.gpu.yml \
  exec gpu-worker python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0)}')"
```

---

## 📋 Environment Variables Reference

All configuration is done via environment variables. Set them in `docker/.env`, a `.env` file in the project root, or directly in your shell.

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `atlas-vox` | Application name |
| `APP_ENV` | `development` | Environment: `development` or `production` |
| `DEBUG` | `true` | Enable debug mode (disable in production) |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | `json` | Log format: `json` or `console` |

### Server Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Allowed CORS origins (JSON array) |

### Docker Port Mapping

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_PORT` | `8100` | Host port for backend API |
| `FRONTEND_PORT` | `3100` | Host port for frontend UI |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./atlas_vox.db` | Database connection string |

**SQLite (default):**
```
DATABASE_URL=sqlite+aiosqlite:///./data/atlas_vox.db
```

**PostgreSQL (production):**
```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/atlas_vox
```

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_DISABLED` | `true` | Skip authentication (homelab mode) |
| `JWT_SECRET_KEY` | `change-me-in-production` | Secret for JWT signing |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRE_MINUTES` | `1440` | JWT token expiry (24 hours) |

### Redis / Celery

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/1` | Redis connection URL |

### Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_PATH` | `./storage` | Root path for audio files and models |

### Provider: ElevenLabs

| Variable | Default | Description |
|----------|---------|-------------|
| `ELEVENLABS_API_KEY` | *(empty)* | ElevenLabs API key |
| `ELEVENLABS_MODEL_ID` | `eleven_multilingual_v2` | TTS model ID |

### Provider: Azure Speech

| Variable | Default | Description |
|----------|---------|-------------|
| `AZURE_SPEECH_KEY` | *(empty)* | Azure subscription key |
| `AZURE_SPEECH_REGION` | `eastus` | Azure region |

### GPU Service

| Variable | Default | Description |
|----------|---------|-------------|
### Provider: GPU Modes

| Variable | Default | Options |
|----------|---------|---------|
| `COQUI_XTTS_GPU_MODE` | `host_cpu` | `host_cpu`, `docker_gpu`, `auto` |
| `STYLETTS2_GPU_MODE` | `host_cpu` | `host_cpu`, `docker_gpu`, `auto` |
| `COSYVOICE_GPU_MODE` | `host_cpu` | `host_cpu`, `docker_gpu`, `auto` |
| `DIA_GPU_MODE` | `host_cpu` | `host_cpu`, `docker_gpu`, `auto` |
| `DIA2_GPU_MODE` | `host_cpu` | `host_cpu`, `docker_gpu`, `auto` |

### Provider: Toggles

| Variable | Default | Description |
|----------|---------|-------------|
| `KOKORO_ENABLED` | `true` | Enable/disable Kokoro |
| `PIPER_ENABLED` | `true` | Enable/disable Piper |
| `PIPER_MODEL_PATH` | `./storage/models/piper` | Path to Piper ONNX models |

---

## 🔌 Port Configuration

Default ports are configured in `docker/.env`:

```env
BACKEND_PORT=8100
FRONTEND_PORT=3100
```

### Changing Ports

Edit `docker/.env` before starting services:
```bash
# Example: use ports 9000 and 9001
BACKEND_PORT=9000
FRONTEND_PORT=9001
```

### Service URLs After Port Change

| Service | URL |
|---------|-----|
| Web UI | `http://localhost:<FRONTEND_PORT>` |
| API | `http://localhost:<BACKEND_PORT>` |
| Swagger | `http://localhost:<BACKEND_PORT>/docs` |
| ReDoc | `http://localhost:<BACKEND_PORT>/redoc` |

---

## 💾 Volume Management

Docker Compose creates three named volumes:

| Volume | Mount Point | Purpose |
|--------|------------|---------|
| `storage_data` | `/app/storage` | Audio files, models, preprocessed data |
| `db_data` | `/app/data` | SQLite database file |
| `redis_data` | `/data` | Redis persistence |

### Inspecting Volumes

```bash
# List volumes
docker volume ls | grep atlas-vox

# Inspect a volume
docker volume inspect atlas-vox_storage_data
```

### Backing Up Volumes

```bash
# Backup all data
docker run --rm \
  -v atlas-vox_storage_data:/source:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/storage_$(date +%Y%m%d).tar.gz -C /source .

docker run --rm \
  -v atlas-vox_db_data:/source:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/db_$(date +%Y%m%d).tar.gz -C /source .
```

### Restoring Volumes

```bash
# Restore storage
docker run --rm \
  -v atlas-vox_storage_data:/target \
  -v $(pwd)/backups:/backup:ro \
  alpine tar xzf /backup/storage_20240101.tar.gz -C /target
```

### Cleaning Up

```bash
# Remove all Atlas Vox data (destructive!)
docker compose -f docker/docker-compose.yml down -v
```

---

## 🔒 Reverse Proxy Setup

For production, place Atlas Vox behind a reverse proxy for SSL termination, caching, and security.

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/atlas-vox

upstream atlas_backend {
    server 127.0.0.1:8100;
}

upstream atlas_frontend {
    server 127.0.0.1:3100;
}

server {
    listen 80;
    server_name vox.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name vox.example.com;

    ssl_certificate     /etc/ssl/certs/vox.example.com.crt;
    ssl_certificate_key /etc/ssl/private/vox.example.com.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Frontend
    location / {
        proxy_pass http://atlas_frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API
    location /api/ {
        proxy_pass http://atlas_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeout for synthesis and training
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;

        # Allow large file uploads (audio samples)
        client_max_body_size 50M;
    }

    # WebSocket for training progress
    location /api/v1/training/jobs/ {
        proxy_pass http://atlas_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 3600s;
    }

    # Swagger docs
    location /docs {
        proxy_pass http://atlas_backend;
        proxy_set_header Host $host;
    }
    location /redoc {
        proxy_pass http://atlas_backend;
        proxy_set_header Host $host;
    }
    location /openapi.json {
        proxy_pass http://atlas_backend;
        proxy_set_header Host $host;
    }
}
```

After creating the config:
```bash
sudo ln -s /etc/nginx/sites-available/atlas-vox /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### CORS Configuration

When using a reverse proxy, update the CORS origins:
```bash
CORS_ORIGINS='["https://vox.example.com"]'
```

---

## 🛡️ Production Hardening

### Checklist

```
✅ Set APP_ENV=production
✅ Set DEBUG=false
✅ Generate strong JWT_SECRET_KEY
✅ Set AUTH_DISABLED=false
✅ Switch to PostgreSQL
✅ Run alembic upgrade head
✅ Configure CORS for your domain only
✅ Set provider API keys via environment variables (not UI)
✅ Configure Redis persistence
✅ Set up SSL/TLS via reverse proxy
✅ Set up log aggregation
✅ Configure backup schedule
✅ Set resource limits on containers
```

### Generate JWT Secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### PostgreSQL Setup

```bash
# Create database
createdb atlas_vox

# Set connection string
DATABASE_URL=postgresql+asyncpg://atlas_vox:your_password@db:5432/atlas_vox

# Run migrations
cd backend
alembic upgrade head
```

### Container Resource Limits

Add to `docker-compose.yml`:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2.0"
  worker:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: "4.0"
```

### Redis Persistence

Add to the Redis service in `docker-compose.yml`:
```yaml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
  volumes:
    - redis_data:/data
```

---

## 📦 Backup and Restore

### What to Back Up

| Component | Location | Method |
|-----------|----------|--------|
| Database (SQLite) | `/app/data/atlas_vox.db` | File copy |
| Database (PostgreSQL) | PostgreSQL server | `pg_dump` |
| Audio storage | `/app/storage/` | Volume backup |
| Configuration | `.env` file | File copy |

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh — Run daily via cron
BACKUP_DIR="/backups/atlas-vox/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# SQLite backup
docker compose -f docker/docker-compose.yml exec -T backend \
  cp /app/data/atlas_vox.db /dev/stdout > "$BACKUP_DIR/atlas_vox.db"

# Storage backup
docker run --rm \
  -v atlas-vox_storage_data:/source:ro \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/storage.tar.gz -C /source .

# Keep 30 days of backups
find /backups/atlas-vox -maxdepth 1 -mtime +30 -exec rm -rf {} \;
```

### Restore from Backup

```bash
# Stop services
docker compose -f docker/docker-compose.yml down

# Restore database
docker run --rm \
  -v atlas-vox_db_data:/target \
  -v /backups/atlas-vox/20240101:/backup:ro \
  alpine cp /backup/atlas_vox.db /target/

# Restore storage
docker run --rm \
  -v atlas-vox_storage_data:/target \
  -v /backups/atlas-vox/20240101:/backup:ro \
  alpine tar xzf /backup/storage.tar.gz -C /target

# Start services
docker compose -f docker/docker-compose.yml up -d
```

---

## 📊 Monitoring and Logging

### Log Output

Atlas Vox uses `structlog` for structured JSON logging:

```json
{"event":"atlas_vox_starting","env":"production","debug":false,"timestamp":"2024-01-01T00:00:00Z","level":"info"}
{"event":"provider_health_check","provider":"kokoro","healthy":true,"latency_ms":45,"level":"info"}
```

### Viewing Logs

```bash
# All services
docker compose -f docker/docker-compose.yml logs -f

# Specific service
docker compose -f docker/docker-compose.yml logs -f backend
docker compose -f docker/docker-compose.yml logs -f worker

# Last 100 lines
docker compose -f docker/docker-compose.yml logs --tail=100 backend
```

### Health Check Endpoint

```bash
curl http://localhost:8100/api/v1/health
# Returns: {"status":"healthy","service":"atlas-vox","version":"0.1.0"}
```

### Monitoring Integration

For Prometheus/Grafana, use the health endpoint as a scrape target or add a `/metrics` endpoint.

For log aggregation (ELK, Loki), configure Docker logging driver:
```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 📈 Scaling Considerations

### Celery Workers

Scale training throughput by adding workers:
```bash
docker compose -f docker/docker-compose.yml up --scale worker=3 -d
```

### GPU Workers

Each GPU worker claims one GPU. For multi-GPU systems:
```yaml
services:
  gpu-worker-1:
    # ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["0"]
              capabilities: [gpu]
  gpu-worker-2:
    # ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["1"]
              capabilities: [gpu]
```

### Database Scaling

- **SQLite**: Single-writer, suitable for development and single-user deployments
- **PostgreSQL**: Multi-writer, connection pooling, suitable for production and multi-user deployments

For PostgreSQL connection pooling, consider PgBouncer:
```
DATABASE_URL=postgresql+asyncpg://user:pass@pgbouncer:6432/atlas_vox
```

---

---

<div align="center">

[Back to User Guide](USER_GUIDE.md) | [Troubleshooting](TROUBLESHOOTING.md) | [API Reference](API_REFERENCE.md)

</div>
