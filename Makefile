.DEFAULT_GOAL := help
SHELL := /bin/bash

BACKEND  := backend
FRONTEND := frontend

.PHONY: help install install-backend install-frontend dev dev-backend dev-frontend \
        test lint typecheck fmt check clean \
        hooks hooks-install hooks-update precommit

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --- setup -----------------------------------------------------------------
install: install-backend install-frontend ## Install all dependencies

install-backend: ## uv sync (creates backend/.venv)
	cd $(BACKEND) && uv sync

install-frontend: ## npm install
	cd $(FRONTEND) && npm install

# --- run -------------------------------------------------------------------
dev: ## Run backend and frontend dev servers together
	@trap 'kill 0' EXIT; \
	( cd $(BACKEND) && uv run uvicorn app.main:app --reload --port 8000 ) & \
	( cd $(FRONTEND) && npm run dev ) & \
	wait

dev-backend: ## Backend only
	cd $(BACKEND) && uv run uvicorn app.main:app --reload --port 8000

dev-frontend: ## Frontend only
	cd $(FRONTEND) && npm run dev

# --- quality ---------------------------------------------------------------
test: ## Run backend tests (offline only)
	cd $(BACKEND) && uv run pytest

test-all: ## Run backend tests including integration/bloomberg markers
	cd $(BACKEND) && uv run pytest -m ""

lint: ## ruff check + eslint
	cd $(BACKEND) && uv run ruff check .
	cd $(FRONTEND) && npm run lint

typecheck: ## mypy --strict + tsc --noEmit
	cd $(BACKEND) && uv run mypy app
	cd $(FRONTEND) && npm run typecheck

fmt: ## Format backend python
	cd $(BACKEND) && uv run ruff format .

check: lint typecheck test ## Lint, typecheck, test

# --- pre-commit -------------------------------------------------------------
hooks-install: ## Install pre-commit and register the git hook (run once)
	uv tool install pre-commit
	pre-commit install

hooks: hooks-install

hooks-update: ## Bump the pinned pre-commit hook revisions
	pre-commit autoupdate

precommit: ## Run every pre-commit hook against all files
	pre-commit run --all-files

clean: ## Remove build artifacts and caches
	rm -rf $(FRONTEND)/.next $(FRONTEND)/node_modules $(BACKEND)/.pytest_cache
	find . -name __pycache__ -type d -not -path "*/node_modules/*" -not -path "*/.venv/*" -exec rm -rf {} +
