.PHONY: install check backend-check frontend-check up down

install:
	python3.12 -m venv backend/.venv
	cd backend && .venv/bin/pip install -e '.[dev]'
	cd frontend && npm ci

check: backend-check frontend-check

backend-check:
	cd backend && .venv/bin/ruff check .
	cd backend && .venv/bin/mypy app
	cd backend && .venv/bin/pytest

frontend-check:
	cd frontend && npm run lint
	cd frontend && npm run typecheck
	cd frontend && npm test -- --run
	cd frontend && npm run build

up:
	docker compose up --build

down:
	docker compose down
