.PHONY: up down test-api test-worker eval lint

up:
	docker compose up --build

down:
	docker compose down -v

test-api:
	cd apps/api && pip install -e ".[dev]" -q && pytest

test-worker:
	cd apps/worker && pip install -e "../api" -q && pip install -e ".[dev]" -q && pytest

test-web:
	cd apps/web && npm install && npm run typecheck && npm run build

eval:
	cd apps/worker && pip install -e "../api" -q && pip install -e ".[dev]" -q && python -m ordo_worker.eval

check-models:
	cd apps/api && python -m ordo_api.ai.check_models

lint:
	cd apps/api && ruff check .
	cd apps/web && npm run lint
