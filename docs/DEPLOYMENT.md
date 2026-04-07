# Atlas Vox Deployment Guide

> Complete guide for deploying Atlas Vox in development, staging, and production environments.

---

## Table of Contents

- [Docker Compose Deployment](#-docker-compose-deployment)
- [GPU Deployment](#-gpu-deployment)
- [Environment Variables Reference](#-environment-variables-reference)
- [Port Configuration](#-port-configuration)
- [Volume Management](#-volume-management)
- [Security Headers](#-security-headers)
- [Reverse Proxy Setup](#-reverse-proxy-setup)
- [Production Hardening](#-production-hardening)
- [Backup and Restore](#-backup-and-restore)
- [Monitoring and Logging](#-monitoring-and-logging)
- [Monitoring Stack (Prometheus + Grafana)](#-monitoring-stack-prometheus--grafana)
- [Scaling Considerations](#-scaling-considerations)

---

## Docker Compose Deployment

Atlas Vox ships with production-ready Docker Compose configurations.

### Architecture

```
docker-compose.yml
├── backend       (FastAPI on :8000, Python 3.11, 4G memory limit)
├── frontend      (Nginx serving React build on :80)
├── postgres      (PostgreSQL 16 Alpine on :5432)
├── redis         (Redis 7 Alpine on :6379, password-protected, 512M limit)
├── worker        (Celery worker, same image as backend, 8G memory limit)
└── celery-beat   (Celery Beat scheduler, same image as backend)

docker-compose.gpu.yml (extends above)
└── gpu-worker    (CUDA 12.1, NVIDIA GPU passthrough)

docker-compose.monitoring.yml (optional overlay)
├── prometheus    (Prometheus on :9090)
└── grafana       (Grafana on :3000)
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
| `backend` | `Dockerfile.backend` | 8000 (internal) -> 8100 (host) | FastAPI API server |
| `frontend` | `Dockerfile.frontend` / `nginx:alpine` | 80 (internal) -> 3100 (host) | Serves React build |
| `postgres` | `postgres:16-alpine` | 5432 (internal only) | PostgreSQL database |
| `redis` | `redis:7-alpine` | 6379 (internal only) | Celery broker + cache (password-protected) |
| `worker` | Same as backend | None | Celery background tasks |
| `celery-beat` | Same as backend | None | Periodic task scheduler (audio cleanup, health checks) |

### Health Checks

Docker Compose includes built-in health checks for key services:

- **Backend**: `curl -f http://localhost:8000/api/v1/health` with a 120-second `start_period` to allow model loading
- **Frontend**: `curl -f http://localhost:80` to verify Nginx is serving

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

### .dockerignore

The `.dockerignore` excludes the following from build context to keep images lean:

- `.github/` -- CI/CD workflows
- `*.sqlite*` -- Local SQLite databases
- `*.pyc` -- Python bytecode
- `.coverage` -- Test coverage reports
- `docker-compose.override.yml` -- Local overrides

---

## GPU Deployment

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

## Environment Variables Reference

All configuration is done via environment variables. An `.env.example` file is provided in the project root with all available settings and sensible defaults. Copy it to get started:

```bash
cp .env.example docker/.env
# Edit docker/.env with your values
```

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

| Variable | Default (local) | Default (Docker) | Description |
|----------|-----------------|-------------------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./atlas_vox.db` | `postgresql+asyncpg://atlas_vox:{POSTGRES_PASSWORD}@atlas-vox-postgres:5432/atlas_vox` | Database connection string |
| `POSTGRES_USER` | -- | `atlas_vox` | PostgreSQL username |
| `POSTGRES_PASSWORD` | -- | `atlas-vox-pg` | PostgreSQL password |
| `POSTGRES_DB` | -- | `atlas_vox` | PostgreSQL database name |

**Local development (SQLite):**
```
DATABASE_URL=sqlite+aiosqlite:///./data/atlas_vox.db
```

**Docker deployment (PostgreSQL -- default):**
```
DATABASE_URL=postgresql+asyncpg://atlas_vox:atlas-vox-pg@atlas-vox-postgres:5432/atlas_vox
```

> **Note:** Docker Compose deployments now use PostgreSQL 16 Alpine by default, replacing the previous SQLite configuration. SQLite remains available for local development outside Docker.

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_DISABLED` | `true` | Skip authentication (homelab mode) |
| `JWT_SECRET_KEY` | `change-me-in-production` | Secret for JWT signing (required when `AUTH_DISABLED=false`) |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRE_MINUTES` | `1440` | JWT token expiry (24 hours) |

> **Important:** When `AUTH_DISABLED=false`, you **must** set `JWT_SECRET_KEY` to a strong random value. The Docker Compose file passes this as an environment variable to the backend service.

### Redis / Celery

| Variable | Default (local) | Default (Docker) | Description |
|----------|-----------------|-------------------|-------------|
| `REDIS_URL` | `redis://localhost:6379/1` | `redis://:{REDIS_PASSWORD}@atlas-vox-redis:6379/0` | Redis connection URL |
| `REDIS_PASSWORD` | -- | `atlas-vox-redis` | Redis password |

Redis is configured with `--maxmemory 256mb --maxmemory-policy allkeys-lru` and password authentication in Docker deployments.

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

## Port Configuration

Default ports are configured in `docker/.env` (or copied from `.env.example`):

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

## Volume Management

Docker Compose creates named volumes for persistent data:

| Volume | Mount Point | Purpose |
|--------|------------|---------|
| `pg_data` | PostgreSQL data directory | PostgreSQL database files |
| `redis_data` | `/data` | Redis persistence |
| `storage_data` | `/app/storage` | Audio files, models, preprocessed data |

### Inspecting Volumes

```bash
# List volumes
docker volume ls | grep atlas-vox

# Inspect a volume
docker volume inspect atlas-vox_storage_data
```

### Backing Up Volumes

```bash
# Backup storage
docker run --rm \
  -v atlas-vox_storage_data:/source:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/storage_$(date +%Y%m%d).tar.gz -C /source .

# Backup PostgreSQL (see Backup and Restore section for pg_dump)
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

## Security Headers

The built-in Nginx configuration (`docker/nginx.conf`) applies security headers to all responses served by the frontend:

| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Security-Policy` | Configured CSP | Prevents XSS and data injection |
| `X-Frame-Options` | `SAMEORIGIN` | Prevents clickjacking |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing |
| `Strict-Transport-Security` | HSTS policy | Enforces HTTPS connections |
| `Permissions-Policy` | Restricted | Limits browser feature access |

These are applied automatically in Docker deployments. If using an external reverse proxy, you may want to review `docker/nginx.conf` and decide whether to apply headers at the proxy level instead.

---

## Reverse Proxy Setup

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

## Production Hardening

### Checklist

```
[ ] Set APP_ENV=production
[ ] Set DEBUG=false
[ ] Generate strong JWT_SECRET_KEY (see below)
[ ] Set AUTH_DISABLED=false
[ ] Change POSTGRES_PASSWORD from default
[ ] Change REDIS_PASSWORD from default
[ ] Run alembic upgrade head
[ ] Configure CORS for your domain only
[ ] Set provider API keys via environment variables (not UI)
[ ] Set up SSL/TLS via reverse proxy
[ ] Set up log aggregation
[ ] Configure backup schedule
[ ] Review security headers in docker/nginx.conf
```

### Generate JWT Secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### PostgreSQL Setup (Docker)

PostgreSQL 16 Alpine is included in the Docker Compose stack and starts automatically. No manual database creation is needed.

```bash
# The Docker Compose stack handles database creation via env vars:
POSTGRES_USER=atlas_vox
POSTGRES_PASSWORD=atlas-vox-pg   # CHANGE THIS in production!
POSTGRES_DB=atlas_vox

# The backend connects using:
DATABASE_URL=postgresql+asyncpg://atlas_vox:${POSTGRES_PASSWORD}@atlas-vox-postgres:5432/atlas_vox

# Run migrations (happens automatically on backend startup, or manually):
docker compose -f docker/docker-compose.yml exec backend alembic upgrade head
```

### PostgreSQL Setup (External)

For an external PostgreSQL instance:

```bash
# Create database
createdb atlas_vox

# Set connection string
DATABASE_URL=postgresql+asyncpg://atlas_vox:your_password@db-host:5432/atlas_vox

# Run migrations
cd backend
alembic upgrade head
```

### Container Resource Limits

Resource limits are configured in `docker/docker-compose.yml`:

| Service | Memory Limit | Purpose |
|---------|-------------|---------|
| `backend` | 4G | FastAPI server |
| `worker` | 8G | Celery worker (handles model inference) |
| `redis` | 512M | Broker and cache |
| `postgres` | 512M | Database |

These can be adjusted in the `deploy.resources.limits` section of each service in `docker-compose.yml`.

### Redis Configuration

Redis is pre-configured in Docker Compose with:
- Password authentication (`REDIS_PASSWORD`, default: `atlas-vox-redis`)
- Memory limit: `--maxmemory 256mb`
- Eviction policy: `--maxmemory-policy allkeys-lru`
- Persistent volume: `redis_data`

---

## Backup and Restore

### What to Back Up

| Component | Location | Method |
|-----------|----------|--------|
| Database (PostgreSQL) | Docker volume `pg_data` | `pg_dump` |
| Database (SQLite, local dev) | `./data/atlas_vox.db` | File copy |
| Audio storage | Docker volume `storage_data` | Volume backup |
| Configuration | `.env` file | File copy |

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh -- Run daily via cron
BACKUP_DIR="/backups/atlas-vox/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# PostgreSQL backup
docker compose -f docker/docker-compose.yml exec -T postgres \
  pg_dump -U atlas_vox atlas_vox > "$BACKUP_DIR/atlas_vox.sql"

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

# Restore PostgreSQL
docker compose -f docker/docker-compose.yml up -d postgres
docker compose -f docker/docker-compose.yml exec -T postgres \
  psql -U atlas_vox atlas_vox < /backups/atlas-vox/20240101/atlas_vox.sql

# Restore storage
docker run --rm \
  -v atlas-vox_storage_data:/target \
  -v /backups/atlas-vox/20240101:/backup:ro \
  alpine tar xzf /backup/storage.tar.gz -C /target

# Start services
docker compose -f docker/docker-compose.yml up -d
```

---

## Monitoring and Logging

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
docker compose -f docker/docker-compose.yml logs -f celery-beat

# Last 100 lines
docker compose -f docker/docker-compose.yml logs --tail=100 backend
```

### Health Check Endpoint

```bash
curl http://localhost:8100/api/v1/health
# Returns: {"status":"healthy","service":"atlas-vox","version":"0.1.0"}
```

### Log Aggregation

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

## Monitoring Stack (Prometheus + Grafana)

Atlas Vox includes an optional monitoring stack with Prometheus and Grafana, deployed via a Docker Compose overlay file.

### Starting the Monitoring Stack

```bash
# Start core services + monitoring
docker compose -f docker/docker-compose.yml -f docker/docker-compose.monitoring.yml up -d

# Start everything including GPU and monitoring
docker compose -f docker/docker-compose.yml -f docker/docker-compose.gpu.yml -f docker/docker-compose.monitoring.yml up -d
```

### Components

| Service | Port | Purpose |
|---------|------|---------|
| Prometheus | 9090 | Metrics collection and alerting |
| Grafana | 3000 | Dashboards and visualization |

### Configuration Files

| File | Purpose |
|------|---------|
| `docker/monitoring/prometheus.yml` | Prometheus scrape configuration |
| `docker/monitoring/grafana/provisioning/datasources/` | Auto-provisioned Prometheus datasource |
| `docker/monitoring/grafana/provisioning/dashboards/` | Pre-built Atlas Vox dashboard |

### Prometheus

Prometheus is configured to scrape the backend metrics endpoint:

- **Target**: `atlas-vox-backend:8000`
- **Path**: `/api/v1/metrics`
- **Interval**: Configured in `docker/monitoring/prometheus.yml`

Access Prometheus at `http://localhost:9090`.

### Grafana

Grafana comes pre-configured with:
- **Datasource**: Prometheus (auto-provisioned, no manual setup needed)
- **Dashboard**: Atlas Vox overview dashboard (auto-provisioned)

Access Grafana at `http://localhost:3000` (default credentials: `admin` / `admin`).

### Metrics Available

The `/api/v1/metrics` endpoint exposes Prometheus-format metrics including:
- HTTP request counts and latencies
- Provider health status
- Synthesis job counts
- Training job progress
- Celery task metrics

---

## Scaling Considerations

### Celery Workers

Scale training throughput by adding workers:
```bash
docker compose -f docker/docker-compose.yml up --scale worker=3 -d
```

### Celery Beat

The `celery-beat` service runs as a single instance and handles periodic tasks:
- **Audio cleanup**: Removes expired temporary audio files
- **Health checks**: Periodic provider health verification

> **Important:** Only one `celery-beat` instance should run at a time to avoid duplicate task scheduling.

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

- **SQLite**: Single-writer, suitable for local development only
- **PostgreSQL** (Docker default): Multi-writer, connection pooling, suitable for production and multi-user deployments

For PostgreSQL connection pooling, consider PgBouncer:
```
DATABASE_URL=postgresql+asyncpg://user:pass@pgbouncer:6432/atlas_vox
```

---

---

<div align="center">

[Back to User Guide](USER_GUIDE.md) | [Troubleshooting](TROUBLESHOOTING.md) | [API Reference](API_REFERENCE.md)

</div>
