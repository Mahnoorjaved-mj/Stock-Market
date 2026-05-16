.PHONY: help dev test lint format docker-up docker-down migrate fresh-db

help:
	@echo "make dev        - run dev server (waitress) on :5000"
	@echo "make test       - run pytest"
	@echo "make lint       - run ruff"
	@echo "make format     - run black"
	@echo "make docker-up  - bring up Postgres + Redis + MailHog + web via docker-compose"
	@echo "make docker-down - tear down docker-compose stack"
	@echo "make migrate    - apply Alembic migrations"
	@echo "make fresh-db   - drop + recreate schema (DANGER)"

dev:
	cd backend && python wsgi.py

test:
	pytest -q

lint:
	ruff check backend

format:
	black backend

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

migrate:
	alembic upgrade head

fresh-db:
	DROP_AND_REBUILD_SCHEMA=true python -c "import sys; sys.path.insert(0, 'backend'); from db import init_schema; init_schema()"
