.PHONY: dev start stop test lint format migrate docker-up docker-gpu-up docker-down docker-reset seed clean install

# Start with port conflict detection (backend=8100, frontend=3100)
dev:
	@bash scripts/start.sh dev

start:
	@bash scripts/start.sh dev

stop:
	@bash scripts/start.sh stop

# Docker — dynamic ports, no conflicts
docker-up:
	@bash scripts/start.sh docker

docker-gpu-up:
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.gpu.yml up --build -d

docker-down:
	docker compose -f docker/docker-compose.yml down

docker-reset:
	@echo "WARNING: This will DELETE all data (database, storage, Redis)."
	@echo "Run 'make backup' first if you want to preserve data."
	@bash -c 'read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1'
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.gpu.yml down -v

backup:
	@bash scripts/backup-db.sh

# Testing
test:
	cd backend && python -m pytest tests/ -v --tb=short

test-all:
	cd backend && python -m pytest tests/ -v --tb=short
	cd frontend && npm run test

test-cov:
	cd backend && python -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

# Code quality
lint:
	cd backend && ruff check .
	cd frontend && npm run lint

format:
	cd backend && ruff format .
	cd frontend && npm run format

# Database
migrate:
	cd backend && alembic upgrade head

migrate-new:
	cd backend && alembic revision --autogenerate -m "$(msg)"

# Utilities
seed:
	cd backend && python -c "import asyncio; from app.core.database import init_db; from app.services.provider_registry import seed_providers, load_provider_configs; asyncio.run(init_db()); asyncio.run(seed_providers()); asyncio.run(load_provider_configs()); print('✅ Seeding complete - database initialized and providers seeded')"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/dist frontend/node_modules/.vite
	rm -rf backend/*.egg-info

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install
