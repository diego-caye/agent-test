.DEFAULT_GOAL := help
.PHONY: help install up down logs ps lint fmt typecheck test build ci clean

BACKEND := backend
FRONTEND := frontend

help:
	@echo "install    instala dependencias de backend (uv) y frontend (npm)"
	@echo "up         levanta db + backend + frontend con Docker"
	@echo "down       apaga los servicios"
	@echo "logs       sigue los logs de los servicios"
	@echo "lint       ruff check + ruff format --check"
	@echo "fmt        aplica ruff format"
	@echo "typecheck  mypy strict + tsc --noEmit"
	@echo "test       pytest + vitest"
	@echo "build      build de produccion del frontend"
	@echo "ci         lint + typecheck + test + build"

install:
	cd $(BACKEND) && uv sync
	cd $(FRONTEND) && npm install

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

lint:
	cd $(BACKEND) && uv run ruff check .
	cd $(BACKEND) && uv run ruff format --check .

fmt:
	cd $(BACKEND) && uv run ruff format .
	cd $(BACKEND) && uv run ruff check --fix .

typecheck:
	cd $(BACKEND) && uv run mypy
	cd $(FRONTEND) && npm run typecheck

test:
	cd $(BACKEND) && uv run pytest
	cd $(FRONTEND) && npm run test

build:
	cd $(FRONTEND) && npm run build

ci: lint typecheck test build

clean:
	docker compose down -v
