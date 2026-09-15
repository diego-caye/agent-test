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

DoD: AT de saludo, lead, anti-loop y concurrencia (spec 09: AT-01, AT-02, AT-03, AT-19). **Cumplido.**

- [x] `specs/notes/adk-api.md` con firmas verificadas contra `google-adk==2.9.1`
- [x] Agente "Luis" con instrucción dinámica (callable, no template de `{state_key}`)
- [x] Tool `guardar_lead` con validación Pydantic e ids desde `ToolContext`
- [x] Máquina de estados pura en `domain/`
- [x] `DatabaseSessionService` sobre Postgres + tabla `leads` con Alembic
- [x] SSE de `chat/stream` con el contrato de spec 02
- [x] Endpoints de sesiones (`POST`/`GET`, messages, lead)
- [x] Telemetría base (OTel → Langfuse, no-op sin keys; `trace_id`, latencia, tokens)
- [x] `FakeAdkLlm` (reemplaza al `FakeLlm` provisional de F1, ya como `BaseLlm` real)
- [x] Postgres en el CI para los tests de integración y aceptación

Verificado el 2026-09-15: 52 tests en verde (AT-01, AT-02, AT-03, AT-19 incluidos), mypy strict limpio en 54 archivos, ruff limpio, y la app real en Docker crea sesiones, sirve `/lead`, devuelve 404 ante sesión ajena y degrada con gracia cuando el modelo falla.

Pendiente para fases siguientes: la tool `guardar_lead` expone sus parámetros como opcionales (desviación deliberada de la guía "sin defaults" de ADK, porque el upsert es parcial por diseño). `EventsCompactionConfig` está activo pero sus umbrales no se han afinado con conversaciones largas (F7).

Nota: no hay `LlmProvider` factory todavía — el modelo se pasa como string de env directo a `Agent(model=...)`, que es lo que ADK acepta. La factory con adaptadores aparece en F8, cuando Ollama entre en juego (requiere el extra `google-adk[extensions]`).

## F3 · `feature/hitl` · P0

DoD: AT de HITL (AT-08, AT-09, AT-10). **Cumplido.**

- [x] Spike de confirmación nativa de tools ADK sobre SSE propio — **funciona**, no hace falta fallback
- [x] `ADR-002-hitl.md`
- [x] Tool `solicitar_contacto_humano` con confirmación previa
- [x] Tabla `handoffs` + transiciones `OPEN → IN_PROGRESS → CLOSED`
- [x] `POST /chat/confirmations` (reanuda el stream)
- [x] `GET /handoffs`, `PATCH /handoffs/{id}` (admin con `ADMIN_TOKEN`)

Verificado el 2026-09-15: 58 tests en verde. AT-08 (test drive → confirmación → ticket + etapa `DERIVADO`), AT-09 (cancelar no crea nada y restaura la etapa previa), AT-10 (segundo pedido devuelve el mismo ticket con `ya_existia: true`), más 401 sin token admin, 409 en transición inválida y 404 en handoff inexistente.

Hallazgo importante: el autogenerate de Alembic veía las tablas de ADK (`sessions`, `events`, `app_states`, `user_states`, `adk_internal_metadata`) como sobrantes y emitía `DROP TABLE`. `migrations/env.py` ahora filtra con `include_object` las tablas que no son nuestras.

## F4 · `feature/frontend` · P0

DoD: flujo end-to-end en el navegador. **Código completo; la verificación del camino feliz en navegador está bloqueada por la falta de `GOOGLE_API_KEY` real.**

- [x] Plan de diseño en `docs/ui.md` (paleta azul noche + ámbar, tipografía, layout ASCII, principios y anti-patrones)
- [x] Sidebar de conversaciones + panel de chat + panel dev plegable
- [x] Streaming token a token con cursor, chips de actividad por tool
- [x] Tarjeta HITL con motivo en lenguaje natural y aviso de ticket
- [x] Errores que dicen qué hacer + botón Reintentar
- [x] Tipos generados desde `/openapi.json` (`npm run gen:types`)
- [x] Tests vitest del parser SSE y del reducer del chat (17 casos)
- [ ] **Verificación del camino feliz en navegador** — necesita una `GOOGLE_API_KEY` con billing
- [ ] Feedback 👍/👎 — movido a F7, junto con el endpoint que lo respalda

Verificado el 2026-09-15: `tsc --noEmit` limpio con `noUncheckedIndexedAccess`, `vite build` en verde, 17 tests de vitest en verde, y los tres contenedores arriba con el proxy del frontend llegando al backend. El camino de error sí se puede ejercer hoy (el backend responde `error` con el placeholder de API key) pero el de streaming, chips y tarjeta HITL no.

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
