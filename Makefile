.DEFAULT_GOAL := help
.PHONY: help install up up-llm rebuild down logs ps lint fmt typecheck test build ci clean migrate ingest-kb

BACKEND := backend
FRONTEND := frontend

help:
	@echo "install    instala dependencias de backend (uv) y frontend (npm)"
	@echo "up         levanta db + backend + frontend con Docker"
	@echo "up-llm     ademas levanta Ollama dentro del proyecto (perfil local-llm)"
	@echo "rebuild    reconstruye las imagenes (solo si cambian dependencias)"
	@echo "down       apaga los servicios"
	@echo "migrate    aplica las migraciones de Alembic"
	@echo "ingest-kb  (re)ingesta la base de conocimiento (RAG) dentro del contenedor"
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

# Sin --build: backend y frontend montan el codigo y recargan solos, asi que
# reconstruir en cada arranque solo cuesta tiempo. Ver rebuild.
up:
	docker compose up -d

up-llm:
	docker compose --profile local-llm up -d

# Necesario solo cuando cambian uv.lock, package-lock.json o los Dockerfile.
rebuild:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

migrate:
	cd $(BACKEND) && uv run alembic upgrade head

# scripts/ y kb/ se montan en el propio backend (docker-compose.yml) para
# esto: quien clone el repo con solo Docker, sin uv/Python nativo, puede
# ingestar la KB igual.
ingest-kb:
	docker compose exec backend uv run python scripts/ingest_kb.py

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
