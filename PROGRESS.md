# PROGRESS.md

Entrega: viernes 18-sep-2026, 15:00 (hora Perú). Actualizar al cerrar cada ítem.

## F0 · `docs/specs` · P0

DoD: specs, `CLAUDE.md` y `PROGRESS.md`. **Parar para revisión.**

- [x] `specs/00-baseline-analysis.md`
- [x] `specs/01-architecture.md`
- [x] `specs/02-api-contract.md`
- [x] `specs/03-tools.md`
- [x] `specs/04-dialog-state.md`
- [x] `specs/05-agent-policy.md`
- [x] `specs/06-memory-rag.md`
- [x] `specs/07-guardrails.md`
- [x] `specs/08-observability-feedback.md`
- [x] `specs/09-acceptance-tests.md`
- [x] `specs/10-priorities.md`
- [x] `specs/11-llm-providers.md`
- [x] `specs/decisions/ADR-001-framework.md`
- [x] `specs/open-questions.md`
- [x] `CLAUDE.md`
- [x] `PROGRESS.md`
- [x] Repo git local inicializado (`main`, `develop`, `docs/specs`), `.gitignore` con `.local/` y `.env`
- [x] **Revisión humana de F0** — aprobada 2026-09-15; merge `docs/specs → develop`

Prerrequisitos aún pendientes (detalle en `specs/open-questions.md`): repo remoto en GitHub + `gh auth login`, skills ADK (`npx skills add google/agents-cli`), `GOOGLE_API_KEY` real.

## F1 · `feature/scaffold` · P0

DoD: `make up` y `make lint typecheck test` en verde. **Cumplido.**

- [x] Estructura de carpetas (`backend/src/asesor/...`, `frontend/src/...`)
- [x] `Settings` (pydantic-settings) con validación de combinaciones de provider
- [x] `docker-compose.yml` (db pgvector + backend + frontend) + `Makefile`
- [x] `.env.example` comentado, con IDs de modelo verificados
- [x] CI (ruff, mypy, pytest, tsc, build)
- [x] `GET /healthz`
- [x] `FakeLlm` determinista
- [x] Plantilla de PR (`.github/pull_request_template.md`)

Verificado el 2026-09-15: `ruff check` + `ruff format --check` limpios, `mypy --strict` sin errores en 20 archivos, 17 tests pytest en verde, `tsc --noEmit` y `vite build` en verde, y `docker compose up` con los tres servicios *healthy* respondiendo `/healthz` (directo y a través del proxy del frontend). `google-adk==2.9.1` importa en el entorno.

## F2 · `feature/agent-core` · P0

DoD: AT de saludo, lead, anti-loop y concurrencia (spec 09: AT-01, AT-02, AT-03, AT-19).

- [ ] `specs/notes/adk-api.md` con firmas verificadas
- [ ] `LlmProvider` factory (Gemini)
- [ ] Agente "Luis" + instrucción por template
- [ ] Tool `guardar_lead`
- [ ] Máquina de estados (`domain/`)
- [ ] `DatabaseSessionService` sobre Postgres
- [ ] SSE de `chat/stream`
- [ ] Telemetría base (trace_id, spans mínimos)

## F3 · `feature/hitl` · P0

DoD: AT de HITL (AT-08, AT-09, AT-10).

- [ ] Spike de confirmación nativa de tools ADK sobre SSE propio
- [ ] `ADR-002-hitl.md`
- [ ] Tool `solicitar_contacto_humano`
- [ ] Tabla `handoffs` + transiciones
- [ ] `POST /chat/confirmations`
- [ ] `GET /handoffs`, `PATCH /handoffs/{id}` (admin)

## F4 · `feature/frontend` · P0

DoD: flujo end-to-end en el navegador.

- [ ] Plan de diseño (colores, tipografías, layout ASCII)
- [ ] Sidebar de conversaciones + panel de chat + panel dev
- [ ] Streaming token a token, chips de actividad
- [ ] Tarjeta HITL
- [ ] Feedback 👍/👎
- [ ] Tipos desde OpenAPI, tests vitest (parser SSE, reducer)

## F5 · `feature/rag` · P0

DoD: AT de RAG y sin datos (AT-06, AT-07).

- [ ] `kb/*.md` (15–18 documentos)
- [ ] `scripts/ingest_kb.py` (idempotente por hash)
- [ ] Tabla `kb_chunks` + índice HNSW
- [ ] Tool `search_knowledge_base`
- [ ] Chequeo de `embedding_model` al arrancar

## F6 · `feature/guardrails` · P0 (L2/L4 P1)

DoD: AT de guardrails y fallos (AT-11 a AT-18).

- [ ] L1 determinista
- [ ] L3 (tools)
- [ ] Fallbacks de tool/modelo/RAG/DB
- [ ] Fault injection (`X-Debug-Fault`)
- [ ] L2 clasificador (P1)
- [ ] L4 salida (P1)

## F7 · `feature/feedback-evals` · P1

DoD: scores visibles en Langfuse; evalset corre.

- [ ] `POST /feedback`
- [ ] Evaluación post-ejecución en background
- [ ] `EventsCompactionConfig` afinado
- [ ] Evalset ADK

## F8 · `feature/local-llm` · P2

DoD: AT principales con Gemma 4.

- [ ] `ADR-003-local-llm.md`
- [ ] `docker-compose.local-llm.yml`
- [ ] `EMBEDDINGS_PROVIDER=ollama` + re-ingesta

## F9 · `docs/release` · P0

DoD: checklist de entrega completo. **Parar antes del merge `develop → main`.**

- [ ] README completo
- [ ] Diagrama Mermaid, antes/después
- [ ] `docs/demo-script.md`
- [ ] Sync specs ↔ código
- [ ] PR `develop → main`
- [ ] Tag `v1.0.0`
- [ ] Video 5–7 min
