# Makefile for Multi-Agent on the Web
# Common development commands

.PHONY: help up down logs restart shell-backend shell-worker test test-backend test-worker clean build format lint install-hooks

# Default target
help:
	@echo "Multi-Agent on the Web - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install-hooks    Install pre-commit hooks"
	@echo ""
	@echo "Docker:"
	@echo "  make up               Start all services"
	@echo "  make down             Stop all services"
	@echo "  make restart          Restart all services"
	@echo "  make logs             View logs from all services"
	@echo "  make build            Rebuild Docker images"
	@echo ""
	@echo "Development:"
	@echo "  make shell-backend    Open backend container shell"
	@echo "  make shell-worker     Open worker-agent container shell"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-backend     Run backend tests"
	@echo "  make test-worker      Run worker-agent tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format           Format code (black, isort)"
	@echo "  make lint             Run linters (pylint, bandit)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove build artifacts and caches"

# Setup
install-hooks:
	pip install pre-commit
	pre-commit install
	@echo "✓ Pre-commit hooks installed"

# Docker commands
up:
	docker-compose up -d
	@echo "✓ All services started"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"

down:
	docker-compose down
	@echo "✓ All services stopped"

restart:
	docker-compose restart
	@echo "✓ All services restarted"

logs:
	docker-compose logs -f

build:
	docker-compose build --no-cache
	@echo "✓ Docker images rebuilt"

# Development shells
shell-backend:
	docker-compose exec backend /bin/bash

shell-worker:
	docker-compose exec worker-agent /bin/bash

# Testing
test: test-backend test-worker
	@echo "✓ All tests completed"

test-backend:
	cd backend && pytest --cov=src tests/ --cov-report=html
	@echo "✓ Backend tests completed. Coverage report: backend/htmlcov/index.html"

test-worker:
	cd worker-agent && pytest --cov=src tests/ --cov-report=html
	@echo "✓ Worker tests completed. Coverage report: worker-agent/htmlcov/index.html"

# Code quality
format:
	@echo "Formatting backend..."
	cd backend && black src/ tests/ && isort src/ tests/
	@echo "Formatting worker-agent..."
	cd worker-agent && black src/ tests/ && isort src/ tests/
	@echo "✓ Code formatting completed"

lint:
	@echo "Linting backend..."
	cd backend && pylint src/
	cd backend && bandit -r src/ -ll
	@echo "Linting worker-agent..."
	cd worker-agent && pylint src/
	cd worker-agent && bandit -r src/ -ll
	@echo "✓ Linting completed"

# Cleanup
clean:
	@echo "Cleaning Python caches..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaning Flutter caches..."
	cd frontend && flutter clean 2>/dev/null || true
	@echo "✓ Cleanup completed"

# Database migrations (will be used in Story 1.2)
migrate:
	cd backend && alembic upgrade head
	@echo "✓ Database migrations applied"

migrate-create:
	@read -p "Enter migration message: " msg; \
	cd backend && alembic revision --autogenerate -m "$$msg"
	@echo "✓ Migration file created"

# Local development (without Docker)
dev-backend:
	cd backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && flutter run -d chrome

dev-worker:
	cd worker-agent && python src/main.py --config config/agent.yaml
