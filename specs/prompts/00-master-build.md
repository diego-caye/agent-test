# Prompt maestro · Asesor automotriz virtual (n8n → Google ADK)

> **Uso.** Guarda este archivo en `specs/prompts/00-master-build.md`. En Claude Code: `Lee specs/prompts/00-master-build.md y ejecútalo. Empieza en F0 y detente al terminar los specs.` Para reanudar en otra sesión: `Lee CLAUDE.md y PROGRESS.md y continúa con lo pendiente.`

## Prerrequisitos (los prepara el humano)

- Repo en GitHub con ramas `main` y `develop`; `gh auth login` hecho.
- Skills oficiales de ADK instalados: `npx skills add google/agents-cli`.
- `.local/baseline_n8n.json` presente y en `.gitignore`.
- Docker, uv y Node LTS. `.env` con `GOOGLE_API_KEY` (billing activo) y, opcional, keys de Langfuse.

## 0. Rol y protocolo

Actúas como tech lead e implementador de este proyecto.

1. **Spec-Driven Development.** F0 solo produce especificaciones; nada de código de aplicación hasta que yo apruebe. Después de F0, la fuente de verdad es `specs/` + `CLAUDE.md`: no releas este archivo completo en cada sesión.
2. **Una rama por fase** desde `develop` → commits convencionales atómicos → `make lint typecheck test` en verde → PR a `develop` (qué, por qué, cómo probar, AT cubiertos) → merge con merge commit, sin squash, para que el grafo muestre las ramas.
3. **Paradas obligatorias:** al terminar F0; ante bloqueos o decisiones que los specs no cubren (anótalas en `specs/open-questions.md` y pregunta); antes del merge `develop → main`. Fuera de eso, avanza de fase en fase.
4. **Reanudable.** Mantén `PROGRESS.md` en la raíz (checklist por fase con su DoD) y actualízalo al cerrar cada ítem. Si el contexto crece demasiado: cierra el ítem, commitea, actualiza PROGRESS y avísame para abrir una sesión nueva.
5. **Specs vivos.** Si el código diverge de un spec, actualiza el spec en el mismo PR. Guarda en `specs/prompts/` cada prompt que te dé.
6. **ADK 2.x no se escribe de memoria.** Usa los skills `google-agents-cli-adk-code`, `google-agents-cli-eval` y `google-agents-cli-observability`, y verifica cada clase y firma en el paquete instalado antes de usarla. No uses el scaffold de agents-cli. No leas archivos enormes completos: busca lo puntual.
7. **Confidencialidad.** Nada de `.local/` entra al historial. Parafrasea los requisitos. El repo no menciona marcas ni empresas del proceso de selección.

## 1. Contexto y requisitos

Reto técnico (AI Engineer): migrar a código el bot "asesor automotriz" que hoy es un workflow n8n (`.local/baseline_n8n.json`). El núcleo decisional va en Google ADK 2.x, desacoplado de la UI; una UI web de chat en tiempo real lo consume por API. Asesoría **general**: sin marcas, sin precios, sin sistemas de fondos colectivos. Entrega: **viernes 18-sep-2026, 15:00 (hora Perú)**: repo público + video de 5–7 min.

Requisitos (parafraseados):
- Replicar la lógica conversacional del baseline en código.
- UI de chat en tiempo real conectada al backend por API.
- Memoria multi-turn por sesión y por usuario en SQL.
- Tools: `guardar_lead` (extracción y persistencia estructurada de datos de contacto y nivel de interés); `solicitar_contacto_humano` (HITL ante test drive, cotización formal o escalado); `search_knowledge_base` (RAG con guías de carrocerías, motorizaciones y mantenimiento).
- HITL: interrupción, derivación o confirmación asistida, también cuando la intención excede los permisos del bot.
- Feedback loop: evaluaciones de calidad post-ejecución (opcional en el reto; aquí P1).
- Guardrails y fallbacks: inyección de prompt, fuera de tópico, fallos de tools y APIs.
- Observabilidad: trazas con trayectoria de tools, latencia por turno y tokens in/out.
- Entregables: repo modular con buena gestión de ramas; `/specs` (contratos de API y tools, estados del diálogo y políticas, tests de aceptación y guardrails); README (setup local y Docker con `.env.example`, justificación del framework, diagrama con memoria, tools, HITL y guardrails); video (interacción, excepciones, tools y vista de trazas).

Rúbrica: SDD y prompting 20% · arquitectura agente + UI 25% · harness 20% · memoria + RAG 15% · UX 10% · observabilidad 10%.

## 2. Decisiones cerradas

| Área | Decisión |
|---|---|
| Backend | Python 3.12, uv, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2 async + Alembic, `google-adk>=2` pineado a versión exacta |
| Agente | Un `Agent` ("Luis") + 3 tools + Plugins ADK. Las tools son adaptadores delgados sobre servicios de aplicación |
| API | FastAPI propio con SSE sobre el `Runner` (`run_async` + streaming parcial; verifica su configuración en 2.x). No se expone `adk api_server` |
| LLM | Puerto `LlmProvider` con dos adaptadores: **Gemini** (default; AI Studio o Vertex vía `GOOGLE_GENAI_USE_VERTEXAI`) y **Ollama/Gemma 4** vía LiteLLM. Modelos solo por env: `AGENT_MODEL`, `GUARDRAIL_MODEL`, `EVAL_MODEL`, `FALLBACK_MODEL` |
| Sesiones | `DatabaseSessionService` de ADK sobre PostgreSQL |
| Tablas propias | `leads`, `handoffs`, `feedback`, `evaluations`, `kb_chunks` (Alembic) |
| RAG | pgvector en el mismo Postgres, `vector(768)`, HNSW coseno. Puerto `Embeddings`: Gemini (`gemini-embedding-001` o `gemini-embedding-2` a 768 dims) u Ollama (`embeddinggemma`) |
| Observabilidad | OpenTelemetry + `openinference-instrumentation-google-adk` → Langfuse. Sin keys: exporter no-op y la app funciona igual |
| Frontend | React + Vite + TypeScript strict + Tailwind; tipos generados del OpenAPI con `openapi-typescript` |
| Infra | `docker-compose.yml` (db, backend, frontend) + overrides `docker-compose.local-llm.yml` y `docker-compose.gpu.yml`; Makefile |
| Idiomas | Código en inglés; specs y README en español; el bot habla español de Perú, tuteando |
| Git | `main` ← `develop` ← `feature/*` · `docs/*` · `fix/*`; PR por fase; tag `v1.0.0` |

## 3. Arquitectura

```
backend/src/asesor/
  main.py            app factory + lifespan (db, telemetría, runner)
  config.py          Settings; valida combinaciones de provider
  api/               routers, DTOs, dependencia X-User-Id, mapeo eventos ADK → SSE
  application/       ChatService, LeadService, HandoffService, KnowledgeService, FeedbackService, EvalService
  domain/            entidades, enums, máquina de estados, puertos (Protocols); sin imports de ADK, FastAPI ni SQLAlchemy
  agent/             factory del Agent, plantilla de instrucción, tools (adaptadores), plugins de guardrails
  infrastructure/    repositorios, retriever pgvector, embeddings, llm factory, clasificador y juez, telemetría, fault injection
backend/tests/{unit,integration,acceptance,evalsets}
backend/scripts/ingest_kb.py
kb/*.md
frontend/src/{api,features/{chat,sessions,hitl,feedback,devpanel},components}
specs/  docs/  .github/{workflows,pull_request_template.md}
```

- Dependencias: `api → application → domain ← infrastructure`; `agent` usa `application`.
- Tipado estricto en código propio (mypy strict; ignores solo para librerías sin tipos). Cobertura ≥ 80% en `domain` y `application`.
- Tests unitarios con un `FakeLlm` determinista, sin red. Tests contra el modelo real marcados `@pytest.mark.live` y fuera de CI.

## 4. Política del agente (spec 05)

Base: la instrucción de "Luis" del baseline (léela del JSON). Conserva rol, voz y frases canned, con estos cambios:
- Inyecta en la instrucción la ficha del lead y la etapa actual: saludo por nombre y anti-loop sin depender del historial.
- Idioma fijado explícitamente.
- Una pregunta por turno, 2–3 oraciones, máximo 2 emojis, sin markdown pesado.
- Consulta `search_knowledge_base` antes de explicar temas técnicos; con `no_results` usa la frase honesta del baseline.
- Nunca precios, cotizaciones, stock ni condiciones de financiamiento: ofrece derivación.
- Teléfono o email solo con consentimiento explícito, explicando para qué se usan.
- "Solo estoy mirando": frase del baseline y bandera `solo_mirando` (menos preguntas proactivas).
- Canary token en la instrucción para detectar fugas.
- Muestreo: con Gemini 3.x no fijes `temperature` (Google recomienda dejar el default 1.0; valores bajos pueden causar loops). El `0.2` del baseline no se replica y se documenta como desviación intencional. Nivel de thinking bajo por env si el SDK lo expone.

## 5. Tools (spec 03)

Envelope común: `{status: "ok" | "no_results" | "error", data?, error?: {code, message, retryable}}`. `session_id` y `user_id` salen de `ToolContext`, nunca de argumentos del LLM. Validación con Pydantic; un error de validación vuelve como `status=error` y el agente pide el dato con naturalidad.

**`guardar_lead`** · upsert parcial del lead del usuario
- `nombre?: str (1–80)`
- `telefono?: str` normalizado (9 dígitos Perú o E.164) · `email?: EmailStr`
- `canal_preferido?: WHATSAPP | LLAMADA | EMAIL | CHAT`
- `consentimiento_contacto?: bool`: obligatorio `true` si llega teléfono o email; si no, `error.code = CONSENT_REQUIRED`
- `uso_principal?: CIUDAD | TRABAJO | FAMILIA | VIAJES | MIXTO`
- `tipo_vehiculo_interes?: SUV | SEDAN | HATCHBACK | PICKUP | VAN | CROSSOVER | OTRO`
- `motorizacion_interes?: GASOLINA | DIESEL | HIBRIDO | ELECTRICO | GLP_GNV | NO_DEFINIDO`
- `nivel_interes?: BAJO | MEDIO | ALTO` (lo extrae el LLM de señales de la conversación)
- La etapa la calcula el dominio (sección 6), no el LLM. Devuelve la ficha y la etapa; emite `lead.updated`.

**`solicitar_contacto_humano`** · derivación asistida
- `motivo: TEST_DRIVE | COTIZACION_FORMAL | COMPRA_INMEDIATA | DISCONFORMIDAD | FUERA_DE_ALCANCE`
- `resumen_requerimiento: str (10–500)` · `canal_preferido?` · `urgencia?: BAJA | MEDIA | ALTA`
- Requiere confirmación del usuario antes de ejecutarse (sección 8).
- Idempotente: máximo 1 handoff `OPEN` por sesión; si existe, lo devuelve.
- Crea el handoff (`OPEN → IN_PROGRESS → CLOSED`) y la etapa pasa a `DERIVADO`.

**`search_knowledge_base`** · equivale al nodo `base_conocimientos_autos` del baseline
- `query: str` · `categoria?: CARROCERIAS | SEGMENTOS | MOTORIZACION | TRANSMISION | CONSUMO | MANTENIMIENTO | SEGURIDAD | USO | GLOSARIO` · `top_k: int = 4 (1–8)`
- Devuelve `[{chunk_id, title, categoria, source, score, content}]`; si el mejor score < `RAG_MIN_SCORE`, `no_results`.

## 6. Estados del diálogo (spec 04)

`NUEVO → DESCUBRIMIENTO → INTERES_CONCRETO → DERIVACION_PENDIENTE → DERIVADO`

| Transición | Guard |
|---|---|
| NUEVO → DESCUBRIMIENTO | se conoce `nombre` |
| DESCUBRIMIENTO → INTERES_CONCRETO | `uso_principal` + (`tipo_vehiculo_interes` o `motorizacion_interes`), o `nivel_interes = ALTO` |
| cualquiera → DERIVACION_PENDIENTE | se propone `solicitar_contacto_humano` y se pide confirmación |
| DERIVACION_PENDIENTE → DERIVADO | el usuario confirma |
| DERIVACION_PENDIENTE → etapa previa | el usuario cancela |

Solo hacia adelante salvo la cancelación. Bandera `solo_mirando`. El spec detalla por transición: trigger, guard, acción, tool y evento SSE, con `stateDiagram-v2`.

## 7. Memoria y sesiones (spec 06)

- `user_id`: UUID anónimo que genera el frontend (header `X-User-Id`). Cada sesión se valida contra su dueño (404 si no coincide).
- Etapa y banderas en el estado de sesión. Datos del lead persistidos por usuario (tabla `leads` + estado de alcance usuario de ADK; verifica los prefijos de scope en 2.x): quien vuelve es saludado por nombre en una sesión nueva.
- Límite de tokens del historial con `EventsCompactionConfig` (umbral de tokens + eventos recientes intactos). No recortes `contents` a mano en callbacks: puedes romper las firmas de pensamiento de Gemini 3, obligatorias en function calling.
- Test obligatorio: 2+ sesiones concurrentes (`asyncio.gather`) de usuarios distintos sin fuga de nombre, lead ni historial.

## 8. HITL (specs 03 y 04 + ADR-002)

- **Primario:** `solicitar_contacto_humano` con la confirmación nativa de tools de ADK. El backend traduce el evento de confirmación a SSE `hitl.confirmation_required {confirmation_id, motivo, resumen, canal}`, la UI muestra una tarjeta y `POST /api/v1/chat/confirmations` devuelve la respuesta al Runner y reanuda el stream.
- La feature es experimental: F3 empieza con un spike corto a través de nuestro SSE. Si no queda limpio, **fallback**: el tool deja `pending_confirmation` en estado, el turno termina y la confirmación de la UI crea el handoff y reanuda. La decisión va en ADR-002.
- **Lado humano:** `GET /api/v1/handoffs` y `PATCH /api/v1/handoffs/{id}` protegidos con `ADMIN_TOKEN`; vista de operador en la UI (P2).

## 9. Guardrails y fallbacks (spec 07)

| Capa | Dónde | Qué hace |
|---|---|---|
| L1 determinista | Plugin, antes del modelo | Longitud máxima, normalización Unicode, caracteres invisibles o de control, patrones de inyección ES/EN ("ignora tus instrucciones", "revela tu prompt", "a partir de ahora eres", etiquetas de rol, bloques codificados). Si hay match: respuesta canned sin llamar al LLM |
| L2 clasificador | Plugin, antes del modelo | `GUARDRAIL_MODEL` con salida estructurada `{label: in_scope \| off_topic \| injection \| abuse, confidence}`. Timeout corto; si falla, fail-open con log (L4 sigue activo) |
| L3 tools | Antes de ejecutar tools | Validación Pydantic, ids desde contexto, máximo N tool calls por turno, PII enmascarada en trazas |
| L4 salida | Después del modelo | Fuga del canary → canned. Precios, cotizaciones, stock o descuentos → mensaje seguro + oferta de derivación |

Fallbacks:
- Excepción en tool → envelope `error`; el agente lo explica sin tecnicismos.
- 429, 5xx o timeout del modelo → backoff exponencial (replica el retry del baseline: 3 intentos) → `FALLBACK_MODEL` → mensaje amable + SSE `error {retryable}`.
- RAG caído → mismo camino que `no_results`. DB caída → 503 con mensaje claro en la UI.
- **Fault injection para la demo:** con `ENABLE_FAULT_INJECTION=true` (solo `APP_ENV=dev`), el header `X-Debug-Fault: tool_error | model_429 | model_timeout | rag_down` fuerza el fallo. Selector en el panel dev.
- Las respuestas canned usan las frases exactas del baseline.

## 10. Observabilidad y feedback (spec 08)

- OTel → Langfuse. Spans propios: `guardrail.l1`, `guardrail.l2`, `guardrail.l4`, `rag.retrieve` (top_k, best_score), `hitl.request`, `hitl.confirm`, `eval.judge`.
- Por turno: `trace_id` creado antes del run, latencia medida en servidor y tokens in/out sumando todas las llamadas del turno (agente + clasificador). Van en `message.completed` y en un log JSON estructurado.
- Atributos: `session_id`, `user_id`, provider, modelo, etapa, `guardrail_blocked`, `hitl`.
- Feedback de usuario: `POST /api/v1/feedback` → tabla `feedback` + score `user-feedback` en Langfuse con el `trace_id`.
- Evaluación post-ejecución (P1): tarea en background con `EVAL_MODEL` y `EVAL_SAMPLE_RATE` que puntúa cada turno (tono empático, brevedad, una sola pregunta, sin precios, fidelidad al contexto RAG) → tabla `evaluations` + scores `quality.*` en Langfuse. Nunca bloquea la respuesta.

## 11. Contrato de API (spec 02)

- `POST /api/v1/sessions` → `{session_id}` · `GET /api/v1/sessions` · `GET /api/v1/sessions/{id}/messages` · `GET /api/v1/sessions/{id}/lead`
- `POST /api/v1/chat/stream` (SSE) · body `{session_id, message}`
- `POST /api/v1/chat/confirmations` (SSE) · body `{session_id, confirmation_id, approved, comment?}`
- `POST /api/v1/feedback` · body `{session_id, trace_id, score: 1 | -1, comment?}`
- `GET /api/v1/handoffs?status=` · `PATCH /api/v1/handoffs/{id}` (admin)
- `GET /healthz` · `GET /readyz` (db + modelo)
- Eventos SSE: `message.delta` · `message.completed {message_id, trace_id, latency_ms, tokens_in, tokens_out, model}` · `tool.started {name}` · `tool.finished {name, status, duration_ms}` · `lead.updated {lead, etapa}` · `hitl.confirmation_required {...}` · `guardrail.triggered {layer, category}` · `error {code, message, retryable}`
- Errores HTTP con cuerpo `{code, message, retryable}`. CORS solo al origen del frontend.

## 12. Base de conocimiento (spec 06)

`kb/` con 15–18 markdown genéricos, sin marcas ni precios, con frontmatter (`title`, `categoria`):
- carrocerías (SUV, crossover, sedán, hatchback, pickup, van)
- catálogo genérico por segmento (plazas, maletero típico, uso ideal, pros y contras)
- gasolina y diésel; GLP y GNV en contexto peruano
- híbridos (MHEV, HEV, PHEV); eléctricos (autonomía y carga)
- transmisiones (MT, AT, CVT, DCT); tracción (4x2, AWD, 4x4)
- consumo y hábitos; mantenimiento básico; seguridad y ADAS
- auto según uso (ciudad, trabajo, familia, viajes, altura)
- checklist de test drive; nuevo vs. seminuevo; glosario

Tono educativo. Al cerrar F5, lista las afirmaciones que debo revisar.

Ingesta idempotente por hash, chunking por encabezados (~400–700 tokens, solapamiento corto), metadatos y columna `embedding_model`. Al arrancar, si el `embedding_model` en DB difiere del configurado: error claro pidiendo re-ingesta (son espacios vectoriales distintos).

## 13. Modelos locales (spec 11 + ADR-003) · P2

- `LLM_PROVIDER=ollama`, `AGENT_MODEL=ollama_chat/gemma4:12b`, `OLLAMA_API_BASE` por env. Usa `ollama_chat/`, no `ollama/`: este último puede provocar loops de tools e ignorar contexto.
- `EMBEDDINGS_PROVIDER=ollama` con `embeddinggemma` (768 dims) + re-ingesta.
- `docker-compose.local-llm.yml`: imagen `ollama/ollama` reciente (Gemma 4 requiere una versión nueva), volumen de modelos, job de pull y `OLLAMA_CONTEXT_LENGTH` explícito (16384 con 12 GB de VRAM, 32768 con 24 GB): Ollama recorta en silencio si el contexto es corto. GPU solo en `docker-compose.gpu.yml` para no romper equipos sin NVIDIA. Alternativa documentada: Ollama nativo en el host con `OLLAMA_API_BASE=http://host.docker.internal:11434`.
- README con tabla de modelos por VRAM (`gemma4:e4b`, `gemma4:12b`, `gemma4:26b`). Corre el subconjunto principal de AT con Gemma y documenta las diferencias frente a Gemini.

## 14. Frontend (spec en `docs/ui.md`)

- Antes de codear, plan de diseño: 4–6 colores con hex, tipografías y roles, layout en ASCII y principios, anclado al mundo automotriz y a usuarios peruanos. Evita los defaults de UI generada: fondo crema con acento terracota, negro con acento neón, kit de tarjetas SaaS idénticas con la misma sombra, etiquetas en mayúsculas sobre cada título y flechas "→" en botones.
- Layout: barra lateral de conversaciones (nueva y lista), panel de chat y panel dev plegable.
- Chat: streaming token a token, indicador de escritura, burbujas cortas, chips de actividad ("Consultando la guía técnica…", "Guardando tus datos…").
- HITL: tarjeta con motivo, requerimiento y canal; botones "Confirmar solicitud" y "Ahora no"; al confirmar, "Solicitud enviada" con el número de ticket.
- Feedback 👍/👎 por respuesta. Errores que dicen qué pasó y qué hacer ("No pudimos conectar con el asesor. Reintenta en unos segundos.") con botón de reintento.
- Panel dev: ficha del lead y etapa en vivo, latencia y tokens por turno, link a la traza (`LANGFUSE_PROJECT_ID`), selector de fault injection (solo dev).
- Calidad: responsive, foco visible, `prefers-reduced-motion`, TS strict + `noUncheckedIndexedAccess`, tipos desde `/openapi.json`, tests con vitest del parser SSE y del reducer del chat.

## 15. Specs de F0

`specs/00-baseline-analysis.md` · `01-architecture.md` (con trade-offs y qué revisar si escala) · `02-api-contract.md` · `03-tools.md` · `04-dialog-state.md` · `05-agent-policy.md` · `06-memory-rag.md` · `07-guardrails.md` · `08-observability-feedback.md` · `09-acceptance-tests.md` · `10-priorities.md` · `11-llm-providers.md` · `decisions/ADR-001-framework.md` (ADK vs. LangGraph vs. mantener n8n) · `open-questions.md` · `CLAUDE.md` · `PROGRESS.md`.

Estilo: concisos (≤ 150 líneas c/u); tablas, esquemas y ejemplos antes que prosa; IDs trazables (`AT-xx`, `GR-xx`, `ST-xx`). ADRs con contexto, opciones, trade-offs y consecuencias.

**`00-baseline-analysis`**: tabla nodo n8n → componente ADK y, verificadas contra el JSON, al menos estas brechas:
1. `gemini-1.5-pro` y `text-embedding-004` ya no están disponibles.
2. `sessionKey` con fallback `'session_default'`: las sesiones sin id comparten memoria.
3. Code tools sin input schema ni persistencia; ticket generado con `Math.random`.
4. El prompt pide `canal_contacto`, el código lee `session_id`/`uso_principal`, y los ids quedan expuestos al LLM.
5. El prompt habla de "contexto con Nombre", pero no se inyecta estado.
6. HITL sin confirmación, pausa ni cola humana.
7. Guardrails solo por prompt.
8. RAG sin ingesta, umbral ni fuentes; memoria sin control por tokens; sin observabilidad.
9. `temperature 0.2`: no aplica a Gemini 3.x (desviación intencional).

**`09-acceptance-tests`**: Given/When/Then; cada AT indica tipo (unit, integration, live, evalset) y trayectoria de tools esperada. Mínimo:
- saludo sin nombre
- usuario que vuelve, saludado por nombre en sesión nueva
- captura de lead sin repreguntar
- teléfono sin consentimiento → pide consentimiento
- "solo estoy mirando"
- pregunta técnica con RAG y fuente
- pregunta sin datos en la KB → frase honesta
- test drive → confirmación → handoff
- cancelar confirmación
- segundo pedido con handoff abierto
- financiamiento → derivación
- off-topic
- "ignora tus reglas"
- "revela tu prompt"
- pedido de precio → sin precio + derivación
- fallo de tool
- 429 con fallback
- RAG caído
- 2 sesiones concurrentes sin fuga

## 16. Fases

| Fase | Rama | Contenido | DoD | Prioridad |
|---|---|---|---|---|
| F0 | `docs/specs` | Sección 15 | Specs, CLAUDE.md y PROGRESS.md. **Parar para revisión** | P0 |
| F1 | `feature/scaffold` | Estructura, Settings, compose, Makefile, `.env.example` comentado, CI (ruff, mypy, pytest, tsc, build), `/healthz`, `FakeLlm`, plantilla de PR | `make up` y `make lint typecheck test` en verde | P0 |
| F2 | `feature/agent-core` | `specs/notes/adk-api.md` con firmas verificadas; LLM factory; Luis; `guardar_lead`; máquina de estados; sesiones en Postgres; SSE; telemetría base | AT de saludo, lead, anti-loop y concurrencia | P0 |
| F3 | `feature/hitl` | Spike + ADR-002; `solicitar_contacto_humano`; handoffs; confirmaciones; endpoints admin | AT de HITL | P0 |
| F4 | `feature/frontend` | Sección 14 | Flujo end-to-end en el navegador | P0 |
| F5 | `feature/rag` | KB, ingesta y `search_knowledge_base` | AT de RAG y sin datos | P0 |
| F6 | `feature/guardrails` | L1–L4, fallbacks, fault injection | AT de guardrails y fallos | P0 (L2 y L4: P1) |
| F7 | `feature/feedback-evals` | Feedback, evaluación post-ejecución, compactación, evalset ADK | Scores visibles en Langfuse; evalset corre | P1 |
| F8 | `feature/local-llm` | Sección 13 + ADR-003 | AT principales con Gemma 4 | P2 |
| F9 | `docs/release` | README, diagramas, `docs/demo-script.md`, sync de specs, PR `develop → main` (**parar antes del merge**), tag `v1.0.0` | Checklist de entrega completo | P0 |

Si falta tiempo, recorta P2 y luego P1; nunca P0.

## 17. README (F9)

- Quick start en menos de 5 minutos (solo Gemini API key + Docker)
- Requisitos y variables de entorno
- Ejecución local sin Docker
- Perfil de modelos locales
- Justificación de ADK (resumen de ADR-001)
- Diagrama Mermaid del flujo migrado, con memoria, tools, HITL y guardrails etiquetados
- Antes/después: captura del workflow n8n y diagrama nuevo
- Tabla baseline → ADK
- Estructura del repo
- Tests, evalset e ingesta
- Observabilidad: qué mirar en Langfuse, con captura
- Decisiones y trade-offs
- Limitaciones y siguientes pasos (ruta a producción en GCP: Cloud Run + Cloud SQL)
- Link a `specs/`

## 18. Guion de demo (`docs/demo-script.md`, 5–7 min)

1. Antes/después: workflow n8n vs. arquitectura nueva (30 s).
2. Conversación feliz: saludo, nombre, uso, tipo, pregunta técnica con RAG; chips de tools; ficha del lead en vivo; sin repreguntas.
3. HITL: pide test drive → tarjeta → confirma → ticket; vista de handoffs.
4. Guardrails: jailbreak, off-topic, pedido de precio.
5. Excepciones con fault injection: fallo de tool y 429 con fallback.
6. Dos sesiones en paralelo sin fuga; usuario que vuelve saludado por nombre.
7. Langfuse: árbol de la traza, tool calls, latencia, tokens in/out, score de feedback y evaluación.
8. Cierre: specs, ramas y PRs; opcional, switch a Gemma 4 local por env.

## 19. Gotchas

- ADK 2.x cambió API, eventos y esquema de sesiones respecto a 1.x: verifica antes de usar.
- `DatabaseSessionService` exige `postgresql+asyncpg://`; Alembic y scripts síncronos usan otro DSN.
- Usa `runner.run_async`, no `run`: con `run` el contexto OTel no llega a los spans.
- La confirmación de tools de ADK es experimental.
- Tras compactar, el modelo puede cambiar de idioma: idioma fijo en la instrucción.
- Gemini 3.x: sin temperature baja y sin manipular el historial a mano.
- Los IDs de modelos Gemini cambian seguido: solo por env; verifica los vigentes en la documentación oficial.
- `gemini-embedding-2` no acepta `task_type`: la tarea va como instrucción en el texto.
- El free tier de Gemini responde 429 rápido: backoff + fallback.
- Ollama: `ollama_chat/`, `OLLAMA_API_BASE`, contexto explícito; cambiar de embeddings exige re-ingesta.
- pgvector indexa hasta 2000 dimensiones en `vector`: por eso 768.

## 20. Checklist de entrega

- Repo público; `main` con tag `v1.0.0`; CI en verde
- README y specs completos
- `.local/` y `.env` fuera del historial (`git log --all -- .local` vacío)
- Video de 5–7 min subido (link) y adjunto si el tamaño lo permite
- Correo con repo y video
