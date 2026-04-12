# Getting Started

## Welcome to Atlas Vox

Atlas Vox is a self-hosted voice training and customization platform with 9 TTS providers, 4 interfaces (Web UI, REST API, CLI, MCP Server), and a complete voice-cloning pipeline. Follow these steps to get up and running.

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| Node.js | 20+ |
| Redis | 7+ |

```bash
python --version   # 3.11+
node --version      # 20+
redis-server --version
```

---

## Step 1: Install Prerequisites

Ensure you have the required tools installed on your system before proceeding.

```bash
python --version   # 3.11+
node --version      # 20+
redis-server --version
```

> Docker is recommended as an alternative -- it bundles everything automatically.

---

## Step 2: Clone and Configure

Clone the repository and copy the example environment file. Adjust settings as needed.

```bash
git clone https://github.com/HouseGarofalo/atlas-vox.git
cd atlas-vox
cp .env.example .env
```

> Default settings work out of the box for local development.

---

## Step 3: Start with Docker (Recommended)

Docker Compose starts the backend, frontend, Redis, and a Celery worker in one command.

```bash
make docker-up
```

> For GPU support: `make docker-gpu-up` (requires NVIDIA Container Toolkit).

---

## Step 4: Or Start Locally

If you prefer a local development setup without Docker, start each service individually.

```bash
# Terminal 1 -- Backend
cd backend && uvicorn app.main:app --reload --port 8100

# Terminal 2 -- Frontend
cd frontend && npm install && npm run dev

# Terminal 3 -- Celery worker
cd backend && celery -A app.tasks.celery_app worker --loglevel=info
```

> Redis must be running on localhost:6379 (database 1).

---

## Step 5: Verify Installation

Open the Web UI and check the Dashboard. Healthy providers show a green badge. CPU-only providers (Kokoro, Piper) are green immediately.

```
http://localhost:3000   # dev frontend
http://localhost:3100   # Docker frontend
http://localhost:8100/docs   # Swagger API docs
```

> Cloud providers (ElevenLabs, Azure) need API keys configured before they go green.

---

## Step 6: Synthesize Your First Voice

Go to the Synthesis Lab, select the default Kokoro provider, type a sentence, and click Synthesize. You should hear audio playback within seconds.

> Browse the Voice Library for 400+ built-in voices across all providers.
