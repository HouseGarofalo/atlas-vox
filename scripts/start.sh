#!/usr/bin/env bash
# Atlas Vox — Startup script with port conflict detection
# Fixed ports: backend=8100, frontend=3100, redis=6379/db1
# Fails fast with clear message if ports are occupied
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Fixed port assignments (change in .env if needed)
BACKEND_PORT=8100
FRONTEND_PORT=3100
REDIS_PORT=6379

# ─── Color helpers ───
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[atlas-vox]${NC} $1"; }
warn() { echo -e "${YELLOW}[atlas-vox]${NC} $1"; }
err()  { echo -e "${RED}[atlas-vox]${NC} $1"; }

# ─── Check if a port is in use (returns 0 if occupied) ───
port_occupied() {
  netstat -ano 2>/dev/null | grep ":$1 " | grep -q LISTEN
}

# ─── Check if a port is used by Atlas Vox (so we can safely kill it) ───
is_atlas_vox_port() {
  local port=$1
  # Check if the process on this port is ours
  local pid
  pid=$(netstat -ano 2>/dev/null | grep ":${port} " | grep LISTEN | awk '{print $5}' | head -1)
  if [ -z "$pid" ]; then return 1; fi
  # Check if the command contains atlas-vox, uvicorn, vite, or celery
  tasklist //FI "PID eq $pid" //FO CSV //NH 2>/dev/null | grep -qi "python\|node\|celery" && return 0
  return 1
}

# ─── Kill Atlas Vox processes on a port ───
kill_port() {
  local port=$1
  for pid in $(netstat -ano 2>/dev/null | grep ":${port} " | grep LISTEN | awk '{print $5}' | sort -u); do
    taskkill //F //PID "$pid" 2>/dev/null && log "  Stopped PID $pid on :${port}"
  done
}

# ─── Determine mode ───
MODE="${1:-dev}"

case "$MODE" in
  dev)
    log "Mode: Local Development"
    log "Ports: backend=:${BACKEND_PORT}  frontend=:${FRONTEND_PORT}  redis=:${REDIS_PORT}/db1"
    echo ""

    # ─── Port conflict checks ───
    CONFLICT=false

    # Backend port
    if port_occupied $BACKEND_PORT; then
      if is_atlas_vox_port $BACKEND_PORT; then
        warn "Port :${BACKEND_PORT} occupied by a previous Atlas Vox process — killing it"
        kill_port $BACKEND_PORT
      else
        err "Port :${BACKEND_PORT} is occupied by another application!"
        err "  Either stop that application, or change PORT in .env"
        CONFLICT=true
      fi
    fi

    # Frontend port
    if port_occupied $FRONTEND_PORT; then
      if is_atlas_vox_port $FRONTEND_PORT; then
        warn "Port :${FRONTEND_PORT} occupied by a previous Atlas Vox process — killing it"
        kill_port $FRONTEND_PORT
      else
        err "Port :${FRONTEND_PORT} is occupied by another application!"
        err "  Change the port in frontend/vite.config.ts"
        CONFLICT=true
      fi
    fi

    if [ "$CONFLICT" = true ]; then
      err ""
      err "Cannot start — resolve port conflicts above, then retry."
      exit 1
    fi

    # ─── Redis check ───
    if python -c "import redis; redis.Redis(port=${REDIS_PORT},db=1,socket_timeout=2).ping()" 2>/dev/null; then
      log "Redis: connected on :${REDIS_PORT}/db1"
    else
      warn "Redis not available on :${REDIS_PORT}"
      if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
        docker rm -f atlas-vox-redis 2>/dev/null
        docker run -d --name atlas-vox-redis -p ${REDIS_PORT}:6379 --restart unless-stopped redis:7-alpine >/dev/null 2>&1
        sleep 2
        if python -c "import redis; redis.Redis(port=${REDIS_PORT},db=1,socket_timeout=2).ping()" 2>/dev/null; then
          log "Redis: started via Docker on :${REDIS_PORT}/db1"
        else
          warn "Redis: could not start. Training/preprocessing will not work."
        fi
      else
        warn "Docker not available. Start Redis manually or run: docker run -d --name atlas-vox-redis -p 6379:6379 redis:7-alpine"
      fi
    fi

    # ─── Clean caches ───
    log "Clearing caches..."
    find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    rm -rf frontend/node_modules/.vite 2>/dev/null || true

    # ─── Start backend ───
    log "Starting backend on :${BACKEND_PORT}..."
    cd backend
    python -m uvicorn app.main:app --host 127.0.0.1 --port "${BACKEND_PORT}" &
    BACKEND_PID=$!
    cd ..

    # Wait for backend health
    log "Waiting for backend..."
    for i in $(seq 1 30); do
      if curl -s "http://127.0.0.1:${BACKEND_PORT}/api/v1/health" >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done

    # Check health result
    HEALTH=$(curl -s "http://127.0.0.1:${BACKEND_PORT}/api/v1/health" 2>/dev/null)
    if echo "$HEALTH" | grep -q '"status"'; then
      log "Backend: healthy"
    else
      err "Backend failed to start!"
      exit 1
    fi

    # ─── Start Celery worker ───
    if python -c "import redis; redis.Redis(port=${REDIS_PORT},db=1,socket_timeout=2).ping()" 2>/dev/null; then
      log "Starting Celery worker..."
      cd backend
      python -m celery -A app.tasks.celery_app worker --loglevel=warning -Q default,preprocessing,training --concurrency=2 &
      cd ..
    fi

    # ─── Start frontend ───
    log "Starting frontend on :${FRONTEND_PORT}..."
    cd frontend
    npx vite --port "${FRONTEND_PORT}" &
    FRONTEND_PID=$!
    cd ..

    sleep 3

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Atlas Vox — Running${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "  Web UI:       ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
    echo -e "  API:          ${GREEN}http://localhost:${BACKEND_PORT}${NC}"
    echo -e "  Swagger:      ${GREEN}http://localhost:${BACKEND_PORT}/docs${NC}"
    echo -e "  Self-Healing: ${GREEN}http://localhost:${BACKEND_PORT}/api/v1/healing/status${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo ""
    echo "Press Ctrl+C to stop all services"
    echo ""

    wait
    ;;

  docker)
    log "Mode: Docker Compose"
    log "Ports: backend=:${BACKEND_PORT}  frontend=:${FRONTEND_PORT}"

    # Check port conflicts
    for port in $BACKEND_PORT $FRONTEND_PORT; do
      if port_occupied $port; then
        err "Port :${port} is occupied! Stop the conflicting service or change docker/.env"
        exit 1
      fi
    done

    # Write ports to docker/.env
    cat > docker/.env <<EOF
BACKEND_PORT=${BACKEND_PORT}
FRONTEND_PORT=${FRONTEND_PORT}
EOF

    log "Building and starting..."
    docker compose -f docker/docker-compose.yml up --build -d

    # Wait for health
    log "Waiting for backend..."
    for i in $(seq 1 60); do
      if curl -s "http://127.0.0.1:${BACKEND_PORT}/api/v1/health" >/dev/null 2>&1; then
        break
      fi
      sleep 2
    done

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Atlas Vox — Docker Stack${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "  Web UI:  ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
    echo -e "  API:     ${GREEN}http://localhost:${BACKEND_PORT}${NC}"
    echo ""
    docker ps --filter "name=atlas-vox" --format "  {{.Names}}: {{.Status}}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    ;;

  stop)
    log "Stopping Atlas Vox..."
    # Docker
    docker compose -f docker/docker-compose.yml down 2>/dev/null || true
    # Local processes
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    log "Stopped"
    ;;

  status)
    echo -e "${CYAN}Atlas Vox Status${NC}"
    echo ""
    for svc in "Backend:${BACKEND_PORT}" "Frontend:${FRONTEND_PORT}"; do
      name="${svc%%:*}"
      port="${svc##*:}"
      if port_occupied "$port"; then
        echo -e "  ${name}: ${GREEN}running on :${port}${NC}"
      else
        echo -e "  ${name}: ${RED}stopped${NC}"
      fi
    done
    if python -c "import redis; redis.Redis(port=${REDIS_PORT},db=1,socket_timeout=2).ping()" 2>/dev/null; then
      echo -e "  Redis:    ${GREEN}running on :${REDIS_PORT}/db1${NC}"
    else
      echo -e "  Redis:    ${RED}not available${NC}"
    fi
    echo ""
    # Docker containers
    if docker ps --filter "name=atlas-vox" --format "{{.Names}}" 2>/dev/null | grep -q atlas-vox; then
      echo "Docker containers:"
      docker ps --filter "name=atlas-vox" --format "  {{.Names}}: {{.Status}}"
    fi
    ;;

  *)
    echo "Usage: $0 {dev|docker|stop|status}"
    echo ""
    echo "  dev    — Start local development (backend + frontend + celery)"
    echo "  docker — Build and start Docker Compose stack"
    echo "  stop   — Stop all Atlas Vox services"
    echo "  status — Show current service status"
    exit 1
    ;;
esac
