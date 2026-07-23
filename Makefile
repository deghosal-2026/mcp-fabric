.PHONY: dev test test-unit test-integration test-e2e lint format typecheck db-up db-migrate db-migrate-new db-downgrade clean opa-test help

help:
	@echo "MCP Fabric - Development Commands"
	@echo "================================="
	@echo "  make dev           Start all services (docker compose up)"
	@echo "  make test          Run full test suite with coverage"
	@echo "  make test-unit     Run unit tests only"
	@echo "  make test-integration  Run integration tests only"
	@echo "  make test-e2e      Run E2E tests only"
	@echo "  make lint          Run ruff + ESLint"
	@echo "  make format        Auto-format Python + TypeScript"
	@echo "  make typecheck     Run mypy type checking"
	@echo "  make db-up         Start PostgreSQL + Redis containers"
	@echo "  make db-migrate    Run pending migrations"
	@echo "  make db-migrate-new  Create new migration (msg=)"
	@echo "  make db-downgrade  Rollback last migration"
	@echo "  make clean         Remove containers + cache files"
	@echo "  make opa-test      Run OPA policy tests"

dev:
	docker compose up

test:
	poetry run pytest tests/ -v --cov=api --cov-report=term-missing

test-unit:
	poetry run pytest tests/ -v -m "unit"

test-integration:
	poetry run pytest tests/ -v -m "integration"

test-e2e:
	poetry run pytest tests/ -v -m "e2e"

lint:
	poetry run ruff check api/ tests/

format:
	poetry run ruff format api/ tests/

typecheck:
	poetry run mypy api/

db-up:
	docker compose up -d postgres redis

db-migrate:
	poetry run alembic upgrade head

db-migrate-new:
	poetry run alembic revision --autogenerate -m "$(msg)"

db-downgrade:
	poetry run alembic downgrade -1

clean:
	docker compose down -v || true
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache

opa-test:
	opa test policies/ -v
