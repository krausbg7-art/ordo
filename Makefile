.PHONY: up down test-api test-worker eval lint

up:
	docker compose up --build

down:
	docker compose down -v

test-api:
	cd apps/api && pip install -e ".[dev]" -q && pytest

test-worker:
	cd apps/worker && pip install -e ".[dev]" -q && pytest

eval:
	cd apps/api && python -m ordo_api.ai.eval

lint:
	cd apps/api && ruff check .
