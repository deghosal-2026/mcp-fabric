.PHONY: dev docker-build docker-up docker-down docker-logs seed-demo \
        test test-unit test-integration test-quick \
        test-ui test-ui-watch test-ui-e2e test-ui-e2e-headed \
        test-e2e-docker lint format typecheck \
        db-up db-migrate db-migrate-new db-downgrade clean opa-test \
        docker-setup help

help:
	@echo "MCP Fabric - Development Commands"
	@echo "================================="
	@echo ""
	@echo "── Docker ──────────────────────────────────────"
	@echo "  make dev                Start full stack (docker compose up)"
	@echo "  make docker-build       Build all Docker images"
	@echo "  make docker-up          Start all services (detached)"
	@echo "  make docker-down        Stop all services"
	@echo "  make docker-logs        Follow logs"
	@echo "  make seed-demo          Load demo data into running Docker DB"
	@echo "  make docker-setup       Run scripts/docker-setup.sh"
	@echo ""
	@echo "── Backend Tests ───────────────────────────────"
	@echo "  make test               Full backend suite + coverage"
	@echo "  make test-unit          Unit tests only (fast)"
	@echo "  make test-integration   Integration tests only"
	@echo "  make test-quick         Unit tests, no coverage (fastest)"
	@echo "  make test-e2e-docker    E2E curl tests against docker-compose"
	@echo ""
	@echo "── UI Tests ────────────────────────────────────"
	@echo "  make test-ui            UI vitest (headless, single run)"
	@echo "  make test-ui-watch      UI vitest (watch mode)"
	@echo "  make test-ui-e2e        Playwright E2E (headless)"
	@echo "  make test-ui-e2e-headed Playwright E2E (visible browser)"
	@echo ""
	@echo "── QA ──────────────────────────────────────────"
	@echo "  make lint               Run ruff + ESLint"
	@echo "  make format             Auto-format Python + TypeScript"
	@echo "  make typecheck          Run mypy type checking"
	@echo "  make opa-test           Run OPA policy tests"
	@echo ""
	@echo "── Database ────────────────────────────────────"
	@echo "  make db-up              Start PostgreSQL + Redis containers"
	@echo "  make db-migrate         Run pending migrations"
	@echo "  make db-migrate-new     Create new migration (msg=)"
	@echo "  make db-downgrade       Rollback last migration"
	@echo ""
	@echo "── Maintenance ─────────────────────────────────"
	@echo "  make clean              Remove containers + cache files"

# ── Docker ─────────────────────────────────────────────────────

dev:
	docker compose up

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

seed-demo:
	docker compose down -v
	docker compose up --build -d
	docker compose exec api sh -c 'until curl -fsS http://localhost:8000/health/ready >/dev/null; do sleep 2; done'
	sh -c 'until curl -fsS http://localhost:3000/login >/dev/null; do sleep 2; done'
	docker compose exec api python -m api.seeders.demo_cli

docker-setup:
	./scripts/docker-setup.sh

# ── Backend Tests ──────────────────────────────────────────────

test:
	poetry run pytest tests/ -v --cov=api --cov-report=term-missing

test-unit:
	poetry run pytest tests/ -v -m "unit"

test-integration:
	poetry run pytest tests/ -v -m "integration"

test-quick:
	poetry run pytest tests/test_errors.py tests/test_models.py tests/test_telemetry.py tests/middleware/ -q --tb=short

test-e2e-docker:
	./tests/e2e/run_e2e.sh

# ── UI Tests ───────────────────────────────────────────────────

test-ui:
	cd ui && npx vitest run --reporter=verbose

test-ui-watch:
	cd ui && npx vitest

test-ui-e2e:
	cd ui && npx playwright test --reporter=list

test-ui-e2e-headed:
	cd ui && npx playwright test --headed --reporter=list

# ── QA ─────────────────────────────────────────────────────────

lint:
	poetry run ruff check api/ tests/
	cd ui && npx eslint src/ 2>/dev/null || true

format:
	poetry run ruff format api/ tests/

typecheck:
	poetry run mypy api/

opa-test:
	opa test policies/ -v

# ── Database ───────────────────────────────────────────────────

db-up:
	docker compose up -d postgres redis

db-migrate:
	poetry run alembic upgrade head

db-migrate-new:
	poetry run alembic revision --autogenerate -m "$(msg)"

db-downgrade:
	poetry run alembic downgrade -1

# ── Maintenance ────────────────────────────────────────────────

clean:
	docker compose down -v || true
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	cd ui && rm -rf dist test-results playwright-report .vitest-results 2>/dev/null || true
