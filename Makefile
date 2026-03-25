.PHONY: dev dev-backend dev-frontend test lint format migrate docker-up docker-gpu-up seed clean

# Development
dev:
	@echo "Starting Atlas Vox development servers..."
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

# Testing
test:
	cd backend && python -m pytest tests/ -v --tb=short

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

# Docker
docker-up:
	docker compose -f docker/docker-compose.yml up --build

docker-gpu-up:
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.gpu.yml up --build

docker-down:
	docker compose -f docker/docker-compose.yml down

# Utilities
seed:
	cd backend && python -m app.cli.main seed

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/dist
	rm -rf backend/*.egg-info

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install
