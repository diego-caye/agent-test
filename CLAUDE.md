# CLAUDE.md

Asesor automotriz virtual — migración de un workflow n8n a Google ADK 2.x + FastAPI + React. Reto técnico (AI Engineer), entrega viernes 18-sep-2026 15:00 (hora Perú).

## Fuente de verdad

Después de F0, **no releas `specs/prompts/00-master-build.md` completo**. Lee `specs/` (specs numerados 00–11, `decisions/ADR-*.md`, `open-questions.md`) y este archivo. `PROGRESS.md` tiene el checklist de fases.

## Reglas operativas

1. **Spec-Driven Development.** Si el código diverge de un spec, actualiza el spec en el mismo PR.
2. **Una rama por fase** desde `develop`: `feature/*`, `docs/*`, `fix/*`. Commits convencionales atómicos → `make lint typecheck test` en verde → PR a `develop` (qué, por qué, cómo probar, AT cubiertos) → merge commit (sin squash).
3. **Paradas obligatorias:** fin de F0 (ya ocurrió); bloqueos o decisiones no cubiertas por specs (anotar en `specs/open-questions.md` y preguntar); antes del merge `develop → main`.
4. **ADK 2.x no se escribe de memoria.** Usa los skills `google-agents-cli-adk-code`, `google-agents-cli-eval`, `google-agents-cli-observability`; verifica cada clase/firma contra el paquete instalado antes de usarla (documentar en `specs/notes/adk-api.md`). No uses el scaffold de agents-cli.
5. **Confidencialidad.** Nada de `.local/` entra al historial (ya está en `.gitignore`). No mencionar marcas ni empresas del proceso de selección.
6. **Idiomas.** Código en inglés; specs y README en español; el bot habla español de Perú, tuteando.
7. **Arquitectura.** `api → application → domain ← infrastructure`; `domain` sin imports de ADK/FastAPI/SQLAlchemy; `agent` usa `application`. Detalle en `specs/01-architecture.md`.

## Decisiones cerradas (resumen; detalle en `specs/01-architecture.md` y `00-master-build.md` §2)

Python 3.12 + uv + FastAPI + Pydantic v2 + SQLAlchemy 2 async + Alembic + `google-adk>=2`. Un `Agent` ("Luis") + 3 tools (`guardar_lead`, `solicitar_contacto_humano`, `search_knowledge_base`) + plugins de guardrails. SSE propio sobre `runner.run_async`. `LlmProvider`: Gemini (default) u Ollama/Gemma 4 vía LiteLLM, solo por env. `DatabaseSessionService` de ADK sobre Postgres + pgvector (`vector(768)`, HNSW coseno) para RAG. OTel → Langfuse (no-op sin keys). Frontend React + Vite + TS strict + Tailwind, tipos desde OpenAPI.

## Estado actual

F0 (specs) y F1 (scaffold) completas y mergeadas a `develop`. **Falta remoto en GitHub y `gh auth login`**, así que los merges de fase se hacen localmente con `git merge --no-ff` y el cuerpo del merge commit hace de descripción de PR — ver `specs/open-questions.md`.

## Comandos

`make` no está instalado en Windows; el `Makefile` es la interfaz canónica (CI, Docker, Linux/macOS) y estos son los equivalentes directos:

```bash
cd backend && uv run ruff check . && uv run ruff format --check .   # lint
cd backend && uv run mypy                                          # typecheck
cd backend && uv run pytest                                        # tests
cd frontend && npm run typecheck && npm run build                  # frontend
docker compose up -d --build                                       # make up
```

En esta máquina los puertos del host están desplazados por el `.env` local (backend 8008, frontend 5174) porque 8000 y 5173 ya están ocupados por otros contenedores.

## Dónde mirar cada cosa

| Pregunta | Spec |
|---|---|
| Qué cambia respecto al baseline n8n | `specs/00-baseline-analysis.md` |
| Estructura de carpetas, capas, trade-offs | `specs/01-architecture.md` |
| Endpoints y eventos SSE | `specs/02-api-contract.md` |
| Contrato de las 3 tools | `specs/03-tools.md` |
| Máquina de estados del diálogo | `specs/04-dialog-state.md` |
| Instrucción del agente | `specs/05-agent-policy.md` |
| Sesiones, memoria, RAG | `specs/06-memory-rag.md` |
| Guardrails L1–L4, fallbacks, fault injection | `specs/07-guardrails.md` |
| Trazas, métricas, feedback, evals | `specs/08-observability-feedback.md` |
| Tests de aceptación | `specs/09-acceptance-tests.md` |
| Qué recortar si falta tiempo | `specs/10-priorities.md` |
| Providers de LLM/embeddings | `specs/11-llm-providers.md` |
| Por qué ADK y no LangGraph/n8n | `specs/decisions/ADR-001-framework.md` |
| Bloqueos y prerrequisitos pendientes | `specs/open-questions.md` |
