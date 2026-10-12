.PHONY: dev test lint fmt migrate up down

dev:      ## run the API with auto-reload
	uv run uvicorn app.api.main:app --reload

test:
	uv run pytest -q

lint:
	uv run ruff check . && uv run mypy app

fmt:
	uv run ruff format . && uv run ruff check --fix .

migrate:
	uv run alembic upgrade head

up:
	docker compose up -d --build

down:
	docker compose down