# Deployment

## Docker Compose Quickstart

Get Atlas Vox running in 3 commands:

**1. Clone the repository**

```bash
git clone https://github.com/HouseGarofalo/atlas-vox.git && cd atlas-vox
```

**2. Configure environment (optional)**

```bash
cp docker/.env.example docker/.env  # Edit as needed
```

**3. Start all services**

```bash
make docker-up  # or: docker compose -f docker/docker-compose.yml up -d
```

---

## Docker Compose Services

| Service | Image / Build | Port | Description |
|---------|--------------|------|-------------|
| `backend` | Build from Dockerfile | 8100 | FastAPI server, REST API, WebSocket, MCP |
| `frontend` | Build from Dockerfile | 3100 | React app served by Nginx |
| `redis` | redis:7-alpine | 6379 | Cache, Celery broker, pub/sub (db 1) |
| `worker` | Same as backend | -- | Celery worker for training/preprocessing |

---

## GPU Deployment

For GPU-accelerated providers (Coqui XTTS, StyleTTS2, CosyVoice, Dia, Dia2), use the GPU Docker Compose configuration:

```bash
# Start with GPU support
make docker-gpu-up

# Or manually:
docker compose -f docker/docker-compose.yml -f docker/compose.gpu.yml up -d

# Prerequisites:
# - NVIDIA GPU with CUDA support
# - NVIDIA Container Toolkit installed
# - Docker configured for GPU passthrough

# Verify GPU access inside container:
docker compose -f docker/docker-compose.yml exec worker nvidia-smi
```

> **VRAM Requirements:** Coqui XTTS (4 GB), StyleTTS2 (2 GB), CosyVoice (3 GB), Dia (6 GB), Dia2 (8 GB). Running multiple GPU providers simultaneously requires sufficient VRAM.

---

## Port Assignments

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| Backend (FastAPI) | 8100 | HTTP | REST API and WebSocket |
| Frontend (Vite/Nginx) | 3100 | HTTP | Web UI |
| Redis | 6379 | TCP | Cache, Celery broker (db 1) |
| MCP Server | 8100 | SSE | Shares backend port, /mcp/sse endpoint |
| Swagger UI | 8100 | HTTP | /docs endpoint |
| ReDoc | 8100 | HTTP | /redoc endpoint |

> **Coexistence with ATLAS:** Atlas Vox uses port 8100 (ATLAS uses 8000), Redis db 1 (ATLAS uses db 0), and a separate SQLite file. Both can run simultaneously.

---

## Docker Environment Variables

These variables are specific to the Docker deployment and are set in `docker/.env`:

```env
# Docker-specific settings
COMPOSE_PROJECT_NAME=atlas-vox
BACKEND_PORT=8100
FRONTEND_PORT=3100
REDIS_PORT=6379

# Resource limits
BACKEND_MEMORY_LIMIT=2g
WORKER_MEMORY_LIMIT=4g
WORKER_CPU_LIMIT=4

# GPU settings (compose.gpu.yml)
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility

# All other Atlas Vox env vars can be set here too
# They will be passed to the backend and worker containers
```

---

## Health Check Verification

After deployment, verify all services are running:

```bash
# Check all containers are running
docker compose -f docker/docker-compose.yml ps

# Backend health check
curl http://localhost:8100/api/v1/health
# Expected: {"status":"healthy","checks":{"database":"ok","redis":"ok","storage":"ok"}}

# Frontend check
curl -s -o /dev/null -w "%{http_code}" http://localhost:3100
# Expected: 200

# Redis check
docker compose -f docker/docker-compose.yml exec redis redis-cli -n 1 ping
# Expected: PONG

# Provider health (all providers)
curl http://localhost:8100/api/v1/providers
# Each provider should have status: "healthy" or "unhealthy" with reason

# Celery worker check
docker compose -f docker/docker-compose.yml exec worker celery -A app.tasks.celery_app inspect ping
# Expected: pong response
```

---

## Production Checklist

- [ ] Set `AUTH_DISABLED=false` and configure `JWT_SECRET` (32+ characters)
- [ ] Use PostgreSQL instead of SQLite for production workloads
- [ ] Set `CORS_ORIGINS` to specific allowed domains (not `*`)
- [ ] Configure HTTPS via reverse proxy (Nginx, Traefik, or Caddy)
- [ ] Set `LOG_LEVEL=WARNING` to reduce log volume
- [ ] Configure backup strategy for `storage/` directory and database
- [ ] Set up monitoring and alerting (Prometheus, Grafana, or similar)
- [ ] Review and set rate limits (`RATE_LIMIT_SYNTHESIS`, `RATE_LIMIT_TRAINING`)
- [ ] Configure webhook subscriptions for critical events
- [ ] Test self-healing system and verify incident notifications
