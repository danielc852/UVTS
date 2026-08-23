SHELL := /bin/sh

.PHONY: setup dev down logs test lint typecheck build theme-check contract contract-check migrate check

setup:
	cd apps/api && uv sync --all-groups
	cd apps/web && pnpm install --frozen-lockfile

dev:
	docker compose --env-file .env -f infra/compose.yaml up --build

down:
	docker compose --env-file .env -f infra/compose.yaml down

logs:
	docker compose --env-file .env -f infra/compose.yaml logs -f

migrate:
	cd apps/api && uv run alembic upgrade head

test:
	cd apps/api && uv run pytest
	cd apps/web && pnpm test -- --run

lint:
	cd apps/api && uv run ruff check .
	cd apps/web && pnpm lint

typecheck:
	cd apps/api && uv run mypy src tests
	cd apps/web && pnpm typecheck

build:
	cd apps/web && pnpm build

theme-check:
	cd apps/web && pnpm build:theme
	git diff --exit-code -- apps/web/src/app/theme/generated

contract:
	cd apps/api && uv run python -m uvts_api.generate_openapi
	cd apps/web && pnpm generate:api

contract-check: contract
	git diff --exit-code -- contracts/openapi.json apps/web/src/api/generated

check: lint typecheck test build theme-check contract-check
