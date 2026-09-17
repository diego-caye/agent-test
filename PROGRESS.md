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

DoD: flujo end-to-end en el navegador. **Cumplido.**

- [x] Plan de diseño en `docs/ui.md` (paleta azul noche + ámbar, tipografía, layout ASCII, principios y anti-patrones)
- [x] Sidebar de conversaciones + panel de chat + panel dev plegable
- [x] Streaming token a token con cursor, chips de actividad por tool
- [x] Tarjeta HITL con motivo en lenguaje natural y aviso de ticket
- [x] Errores que dicen qué hacer + botón Reintentar
- [x] Tipos generados desde `/openapi.json` (`npm run gen:types`)
- [x] Tests vitest del parser SSE y del reducer del chat (17 casos)
- [x] **Verificación del camino feliz en navegador** — desbloqueada con los modelos locales
- [ ] Feedback 👍/👎 — movido a F7, junto con el endpoint que lo respalda

Verificado el 2026-09-15 en Chromium contra el stack real con `qwen3:4b` local: conversación completa, ficha del lead llenándose en vivo en el panel dev (nombre, uso, nivel de interés), chip de etapa, latencia/tokens/modelo del turno, sesión listada en la sidebar. Sin errores de consola y sin scroll horizontal a 390px. `tsc --noEmit` limpio con `noUncheckedIndexedAccess`, `vite build` y 17 tests de vitest en verde.

La captura del navegador fue lo que destapó dos bugs que los tests con el doble no podían ver: el modelo escribiendo `guardar_lead(...)` como texto en la burbuja, y el filtro de categoría del RAG devolviendo `no_results` con la respuesta en la KB.

## F5 · `feature/rag` · P0

DoD: AT de RAG y sin datos (AT-06, AT-07). **Cumplido con el embedder determinista; falta una corrida de ingesta con embeddings reales.**

- [x] `kb/*.md` — 18 documentos, 71 fragmentos, sin marcas ni precios
- [x] `scripts/ingest_kb.py` idempotente por hash (verificado: segunda corrida re-embebe 0)
- [x] Tabla `kb_chunks` + índice HNSW coseno + extensión `vector` creada por la migración
- [x] Tool `search_knowledge_base` con umbral, filtro por categoría y `no_results`
- [x] Chequeo de `embedding_model` al arrancar (falla con mensaje que pide re-ingesta)
- [x] Adaptador de embeddings de Gemini, con el caso especial de `gemini-embedding-2` (sin `task_type`)
- [x] `docs/kb-afirmaciones-a-revisar.md` con las afirmaciones a verificar
- [ ] **Ingesta con embeddings reales** — necesita `GOOGLE_API_KEY`

Verificado el 2026-09-15: 76 tests en verde, mypy strict limpio (71 archivos), ruff limpio. AT-06 (consulta la KB y responde con lo recuperado, con título/fuente/score y en orden de score) y AT-07 (sin datos y con KB vacía devuelve `no_results` y el agente usa la frase honesta del baseline).

Nota sobre el umbral: `RAG_MIN_SCORE` vale 0.55 en producción, calibrado para un embedder real. `FakeEmbeddings` es bolsa de palabras y su distribución de scores es otra (medido sobre la KB real: consulta relevante ~0.55, irrelevante ~0.07), así que los tests usan 0.35. Lo que verifican es el cableado del umbral, no la calidad semántica. **El 0.55 de producción hay que re-calibrarlo con embeddings reales.**

## F6 · `feature/guardrails` · P0 (L2/L4 P1)

DoD: AT de guardrails y fallos (AT-11 a AT-18). **Cumplido salvo L2.**

- [x] L1 determinista: longitud, normalización Unicode, invisibles, patrones ES/EN de inyección
- [x] L3: tope de tool calls por turno (la validación Pydantic y los ids desde `ToolContext` ya venían de F2/F3)
- [x] L4 salida: fuga del canary y precios/cuotas/stock → mensaje seguro
- [x] Fallbacks de tool, modelo (backoff + respaldo), RAG y DB
- [x] Fault injection (`X-Debug-Fault`), solo en dev
- [ ] L2 clasificador (P1) — **no implementado**; L1 + L4 cubren los AT del reto

Verificado el 2026-09-15: 125 tests en verde, mypy strict limpio (83 archivos), ruff limpio. AT-11 a AT-18 cubiertos, incluidos el fallback por 429 y los dos casos de L4.

**Cambio de contrato (spec 02 §4):** el texto ya no se transmite token a token. L4 necesita ver la respuesta completa antes de que salga, y un delta transmitido no se puede retirar del cliente. El backend acumula y emite un solo `message.delta` ya filtrado. Los chips de tools, la ficha y la tarjeta HITL siguen llegando en vivo. **Pendiente al mergear F4:** actualizar `docs/ui.md`, que todavía describe la escritura token a token.

Hallazgo: `FaultInjectionPlugin` no puede inyectar fallos del modelo, porque ADK captura las excepciones de los plugins y `ResilientLlm` nunca vería el 429. Se inyectan dentro de `ResilientLlm` vía un contextvar por request.

## F8 (adelantada) · modelos locales · P2 → hecha en F6

Adelantada a pedido del humano: sin `GOOGLE_API_KEY`, era lo que desbloqueaba verificar F4, la ingesta real y la calibración del umbral de RAG.

- [x] `ADR-003-modelos-locales.md` con los hallazgos de integración
- [x] Adaptadores: `LiteLlm` con `ollama_chat/` para el agente, `OllamaEmbeddings` para la KB
- [x] `google-adk[extensions]` (LiteLLM no viene en la instalación base)
- [x] Ollama en el `docker-compose.yml` bajo el perfil `local-llm` (antes dos archivos de override)
- [x] `.env.example` con los dos perfiles intercambiables
- [x] Validación del prefijo `ollama_chat/` y de `num_ctx` explícito en `Settings`
- [x] KB re-ingerida con `embeddinggemma` y `RAG_MIN_SCORE` calibrado a 0.42
- [x] Conversación real verificada: saludo, captura de lead, RAG, HITL, guardrails y precios

**Modelo del agente: `gemma4:latest` con `OLLAMA_THINK=low` y contexto 32768, 100% en GPU, 5–10 s por turno.**

Llegar ahí requirió dos arreglos de entorno que no son del código y que están documentados en ADR-003:

1. **`%USERPROFILE%\.wslconfig` con `memory=24GB`.** Sin él, WSL toma el 50% de la RAM del equipo y Docker corre dentro de esa VM: Ollama veía 6 GB de RAM del sistema y `gemma4` fallaba con `model requires more system memory`. Requiere `wsl --shutdown`.
2. **Liberar la VRAM que otros contenedores retienen ociosos.** Un servicio de síntesis de voz mantenía su modelo cargado (~4,8 GB) aunque no se usara. Los servicios de ML suelen hacer *eager loading* y PyTorch no devuelve al driver la VRAM que libera.

Con ambos, `gemma4` pasó de repartirse 66% a CPU (19 s/turno) a 100% GPU (5–10 s/turno). `ollama ps` es lo que delata el reparto.

Alternativa si no se puede liberar VRAM: `qwen3:4b` con thinking entra en GPU con bastante menos margen y también llama las tres tools.

## UX de modelos y conversaciones · `feature/ux-modelos-shadcn` · pedida por el humano

Fuera del plan de fases original; se hizo sobre F6 porque es lo que vuelve
demostrable el trabajo de los modelos locales en el vídeo.

- [x] `GET /api/v1/models` y `model_id` por turno, con un `Runner` por modelo
- [x] Selector de modelo en la cabecera (Gemma 4 / Qwen3 / Gemini)
- [x] Título de conversación generado en segundo plano con `GUARDRAIL_MODEL`
- [x] shadcn/ui como base de componentes, con la paleta reexpresada en sus tokens
- [x] Un único `docker-compose.yml` y recarga en caliente de backend y frontend
- [x] L4: pseudo-llamadas a tools con llaves o prefijo (`llama:guardar_lead{…}`)

Verificado el 2026-09-15 en el navegador: 152 tests de backend y 17 de frontend
en verde, mypy strict limpio, sin errores de consola y sin scroll horizontal a
390px. El cambio de modelo a media conversación conserva historial y lead.

El modelo se elige **por turno y no por sesión**: la conversación vive en
`DatabaseSessionService`, así que cambiarlo a media charla no pierde nada. Es la
forma más directa de enseñar el mismo caso con los tres modelos.

### Ronda de corrección · `fix/ux-reintento-modo-oscuro`

Bugs reales encontrados al usar la interfaz recién armada, todos con causa
identificada antes de tocar código:

- [x] **"Nueva conversación" creaba una sesión por clic.** Sin guard: cada
  clic disparaba su propia llamada async antes de que la primera terminara.
  Se guarda la promesa en curso y los clics mientras tanto la reciben en vez
  de crear otra; el botón además se deshabilita. Verificado con 8 clics
  síncronos → 1 sola sesión.
- [x] **El `Select` de modelo se abría encima del propio selector.**
  `position="item-aligned"` (el valor por defecto de shadcn, pensado para
  imitar un `<select>` nativo) alinea la opción elegida con el disparador;
  en una cabecera angosta eso lo tapaba. Cambiado a `position="popper"`.
- [x] **Un turno sin respuesta dejaba la interfaz colgada en "escribiendo"
  para siempre**, sin error ni forma de reintentar. Dos causas cubiertas: (a)
  la conexión SSE se corta sin ningún evento de cierre — se detecta si el
  stream termina sin haber visto `message.completed`/`error`/confirmación/
  handoff; (b) el turno queda en silencio total — timeout de inactividad de
  3 minutos en el cliente (holgado a propósito: un turno sin tools no manda
  ni un byte hasta que L4 termina de revisar la respuesta completa, y Gemini
  con reintentos de proveedor se ha medido en 121 s). Verificado interceptando
  la respuesta SSE con Playwright para forzar el corte silencioso.
- [x] **Paleta monocroma (blanco y negro) con modo claro/oscuro**, a pedido
  del humano en vez de azul noche + ámbar. `ThemeToggle` alterna la clase
  `.dark`, persiste en `localStorage` y sigue el tema del sistema hasta que
  se toca el botón; un script inline evita el parpadeo del tema equivocado
  en la primera pintura.
- [x] Descubierto en el camino: el caché de módulos de Vite (`node_modules/.vite`)
  había quedado con una versión de antes de adoptar shadcn/ui, así que la UI
  que se estaba probando mezclaba componentes viejos y nuevos. `docker compose
  restart` no lo limpia; hace falta borrar el caché a mano una vez.

Verificado el 2026-09-16: 152 tests de backend y 19 de frontend en verde
(2 nuevos para el timeout de inactividad), typecheck y build limpios, cero
errores de consola en el navegador en ambos temas.

### Segunda ronda · `fix/nueva-conversacion-vacia` y `feature/rutas-por-chat`

El reporte de "sigue abriendo varios" persistía tras la ronda anterior porque
esa corrección solo cubría clics simultáneos; clics normales (cada uno
completo antes del siguiente) seguían creando una sesión vacía por clic. La
causa de fondo era otra: el botón creaba la sesión en el backend de
inmediato, así que cualquier repetición —incluida recargar la página con el
borrador sin usar, ya que `sessionId` no sobrevivía a un refresh— dejaba una
fila vacía nueva.

- [x] Primer parche: si ya se está en una conversación vacía, pedir otra
  devuelve la misma en vez de crear una (cubre el caso de clic repetido).
- [x] Arreglo de fondo: cada conversación pasa a tener su propia URL,
  `/c/:id`, navegable de verdad (recarga, pestaña nueva con Ctrl/Cmd+clic,
  atrás/adelante del navegador). `/` es el borrador. "Nueva conversación" ya
  no llama a la API en absoluto: solo vuelve al borrador. La sesión se crea
  recién cuando se envía el primer mensaje real.
- [x] Router propio, sin librería: solo dos formas de URL, así que una
  librería completa de rutas sería más código que resolver, no menos
  (`frontend/src/lib/route.ts`).
- [x] Entrar directo a `/c/:id` con un `id` inexistente o de otro usuario cae
  al borrador en vez de dejar la pantalla colgada.
- [x] Descartada una regresión del banner de reintento: la misma conversación
  del reporte ("holaaa" → "q tal?") se repitió contra el backend real y
  respondió bien las dos veces. La causa más probable del cuelgue reportado
  fueron los reinicios del contenedor del frontend durante las pruebas en
  paralelo, no un bug del cliente.

Verificado en el navegador: 3 clics en el borrador → 0 sesiones creadas;
enviar el primer mensaje → URL cambia a `/c/:id` y crea 1 sesión; recargar
en `/c/:id` conserva la conversación; Ctrl+clic en la barra lateral abre la
misma conversación en una pestaña nueva sin navegar la actual.

### Tercera ronda · `feature/reintento-tras-recarga`

Diagnóstico confirmado con datos, no solo sospecha: se inspeccionó la tabla
`events` en Postgres para la sesión reportada como colgada y se comprobó
que el turno de "q tal?" nunca escribió ningún evento del agente — solo el
mensaje del usuario y, después, el evento del título en segundo plano. Se
reprodujo la misma firma a propósito (mandar un mensaje y cortar la
conexión del cliente a medio turno) y salió el mismo patrón exacto,
incluido el log `Root node luis was cancelled.` de ADK. Los logs del
incidente original ya no existían — el contenedor del backend se había
reconstruido varias veces durante las pruebas en paralelo — así que no se
pudo confirmar la causa puntual, pero el mecanismo general quedó probado:
un cliente que se desconecta a medio turno hace que ADK cancele la tarea
sin persistir nada, ni siquiera un evento de error.

- [x] Al cargar una conversación cuyo último mensaje es del usuario (sin
  respuesta después), se reconstruye la señal de reintento: mismo banner y
  botón "Reintentar" que un fallo en vivo, con el mensaje exacto guardado.
- [x] De paso, "Reintentar" dejó de duplicar la burbuja del mensaje del
  usuario (ya estaba en pantalla, sea por un fallo en vivo o por el
  historial cargado): `send()` ahora recibe `{ echo: false }` para no
  volver a agregarla.
- [x] 2 tests nuevos del reducer para el caso "conversación sin respuesta"
  y el caso "ya tiene respuesta, no muestra el aviso".
- [x] A pedido del humano, el botón "Reintentar" se movió del banner de
  error (al pie de la pantalla, ambiguo con más de un mensaje) a un ícono
  bajo el mensaje concreto que se reenvía — solo el último mensaje puede
  necesitarlo. El banner se queda solo con el texto de qué pasó.

Verificado en el navegador contra una sesión reproducida a propósito: el
banner aparece al abrir `/c/:id`, "Reintentar" reenvía el mismo mensaje sin
duplicar la burbuja y el banner desaparece al llegar la respuesta real.

### Cuarta ronda · `fix/indicador-escritura` y edición del último mensaje

- [x] Los puntos del indicador de escritura eran invisibles en modo oscuro:
  `bg-muted` y `bg-card` son el mismo gris (`#171717`). Cambiado a
  `bg-muted-foreground`, verificado con el color real calculado por el
  navegador en los dos temas.
- [x] El aviso a los 8s afirmaba "suele tardar la primera vez" sin poder
  saberlo — Ollama descarga el modelo de la VRAM tras un rato sin uso, así
  que un turno "no-primero" puede recargar igual. Texto reescrito para no
  depender de esa afirmación.
- [x] A pedido del humano, botón "Editar" junto a "Reintentar": la propia
  burbuja del mensaje se vuelve editable en su lugar (no se manda el texto
  al campo de entrada principal de abajo). Al confirmar, esa misma burbuja
  queda con el texto corregido y se reenvía — no se agrega una aparte.
  Nueva acción de reducer, `edit-last-message`, que reemplaza el contenido
  del último mensaje en vez de añadir uno; `send()` pasa a aceptar un modo
  (`'append' | 'silent' | 'replace-last'`) en vez del booleano `echo`
  anterior, para cubrir los tres casos: mensaje nuevo, reintento tal cual,
  reintento editado.

Verificado en el navegador: clic en "Editar" convierte la burbuja de
"q tal?" en un campo editable con foco; al corregirlo y confirmar, esa
misma burbuja pasa a mostrar el texto nuevo y recibe su respuesta — la
conversación sigue teniendo 2 mensajes, no 3.

### Sidebar de conversaciones con las primitivas oficiales de shadcn

La barra lateral era un `<nav>` a mano, `hidden md:flex`: sin forma de
ocultarla en desktop y sin ninguna versión para pantallas angostas. Se
reemplazó por `Sidebar`/`SidebarProvider`/`SidebarTrigger` de shadcn
(`npx shadcn add sidebar`, que de paso trajo `sheet`, `tooltip`, `input`,
`skeleton` como dependencias) en vez de escribir la animación a mano.

- [x] Botón de alternar (ícono junto al título "Luis") con la animación
  de deslizamiento ya incluida en el componente — verificado con
  Playwright: 1er clic → `data-state="collapsed"`, 2do clic →
  `"expanded"`, cero errores de consola.
- [x] En pantallas angostas pasa a ser un overlay (`Sheet`) en vez de no
  existir, que era el comportamiento anterior — la lista de
  conversaciones ahora es alcanzable en mobile.
- [x] Lista de conversaciones migrada a `SidebarMenu`/`SidebarMenuButton`/
  `SidebarMenuAction`: mismo comportamiento (link real, no botón; borrar
  con confirmación), ahora con el estado activo/hover que trae el
  componente en vez de clases manuales.

### Quinta ronda · catálogo dinámico de Ollama y versiones fijas

A pedido del humano: los modelos de Ollama dejan de declararse a mano en
`MODEL_CHOICES` y se descubren en vivo; de paso, nada de `:latest` en lo
que Docker instala solo.

- [x] `infrastructure/llm/ollama_discovery.py`: `GET /api/tags` + `POST
  /api/show` por modelo, filtra los que no tienen `"completion"` en
  `capabilities` (así `embeddinggemma` nunca aparece en el selector de
  chat) y trae `supports_tools`/`supports_thinking` reales.
- [x] `infrastructure/container.py`: el catálogo (`build_catalog`) mezcla
  lo estático (Gemini, vía `MODEL_CHOICES`) con lo descubierto; una
  entrada de Ollama declarada a mano se ignora a propósito. El modelo por
  defecto es el que coincide con `AGENT_MODEL`, no "el primero de la
  lista" — con descubrimiento dinámico el orden no es una decisión.
  `RunnerRegistry` pasa a resolver sus propios ids en vez de delegar en
  `Settings`, que se queda solo con configuración estática.
  `build_container` pasa a ser async (un único call site, `main.py`).
- [x] `build_base_model` ya no manda `think` siempre al modelo principal:
  solo si `supports_thinking` de la opción elegida es cierto — antes
  mandarlo a un modelo sin esa capacidad tiraba 400 (ADR-003), ahora ya no
  puede pasar con ninguna opción del catálogo.
- [x] `ModelOption`/`ModelSelect`: íconos de razonamiento y herramientas
  por modelo en el desplegable (verificado: `qwen3:4b-instruct` sin ícono
  de razonamiento, `qwen3:4b` con los dos — son variantes con capacidades
  distintas de verdad, no solo de nombre).
- [x] `docker-compose.yml`: `ollama/ollama:0.24.0` fijo (no `:latest`) y
  el job `ollama-pull` ahora baja los **cuatro** modelos que la app usa
  (agente, guardrail/eval, respaldo, embeddings) con tags explícitos —
  antes solo bajaba dos; cualquier turno que tocara el respaldo o el
  guardrail habría fallado con "model not found" la primera vez que hiciera
  falta en una instalación fresca desde GitHub.
- [x] `.env.example` y specs 02/11/ADR-003 sincronizados con el nuevo
  contrato de `GET /api/v1/models` y la política de versiones fijas.
- [x] 11 tests nuevos (`test_ollama_discovery.py`, `test_model_catalog.py`).

Verificado contra el Ollama real de esta máquina: 163 tests de backend en
verde, `GET /api/v1/models` devuelve 5 opciones (4 de Ollama descubiertas
+ Gemini), `embeddinggemma` correctamente ausente, capacidades distintas
por variante confirmadas.

**Verificado con una descarga limpia real**, a pedido del humano: `ollama/ollama:0.24.0` no alcanzaba — `gemma4:12b` necesita Ollama ≥0.30.3 (≥0.30.5 para evitar un crash conocido de esa variante), y `pulling manifest: 412 requires a newer version of Ollama` lo confirmó en la práctica. Se subió el pin a `ollama/ollama:0.34.0` (última estable al momento de fijarlo) y se repitió la descarga:

- `docker exec asesor-ollama-1 ollama list` → los 4 modelos, con los tags exactos de `.env.example`.
- `discover_ollama_models("http://localhost:11435")` (la función real, no una simulación) contra ese Ollama recién bajado → 3 modelos de chat (`embeddinggemma:300m` correctamente ausente), con `supports_tools`/`supports_thinking` reales.
- Dato curioso que confirma por qué esto se descubre en vivo y no se asume: `qwen3:4b-instruct` reportó `thinking=True` en 0.34.0 pero `thinking=False` en la instalación nativa de esta máquina (0.24.0) — la propia versión del motor puede cambiar cómo reporta las capacidades del mismo modelo.

Contenedores `ollama`/`ollama-pull` parados tras la verificación (no borrados: el volumen conserva los modelos, así que `docker compose --profile local-llm up -d` los trae de vuelta sin volver a descargar nada). Sigue pendiente, y sí hace falta si se usa este perfil para la demo: correr `ollama ps` y repetir el ajuste de VRAM/contexto de ADR-003, que está medido contra la instalación nativa, no contra esta.

- [x] `OLLAMA_EXTRA_MODELS` (`.env`, lista separada por espacio): suma modelos al job `ollama-pull` sin editar `docker-compose.yml`. Corrige una confusión real: sumar un modelo al Ollama nativo (`ollama pull` + reiniciar backend) y sumarlo al perfil dockerizado para quien clona el repo son dos caminos distintos — antes el segundo exigía editar el compose a mano. Verificado con la variable vacía (0 pulls de más, `exit 0`) y con un nombre inválido (`pull model manifest: file does not exist`, `exit 1`).

### Sexta ronda · `StaleSessionError` — el título tumbaba turnos reales

Bug encontrado en uso real (no en pruebas sintéticas): un mensaje enviado poco después del primero, o "Reintentar", a veces fallaba con "No pudimos conectar con el asesor" sin relación aparente con Ollama ni Docker. El log real:

```
google.adk.errors._stale_session_error.StaleSessionError: The session has
been modified in storage since it was loaded. Please reload the session
before appending more events.
```

Causa: `TitleService` guardaba el título con `append_event` + `state_delta`
sobre la sesión de ADK — el mismo mecanismo de bloqueo optimista que usa
cualquier turno de chat para escribir su propia respuesta. Si la generación
del título (que corre en segundo plano tras el primer mensaje, spec 08)
terminaba de escribir *mientras* un turno siguiente en la misma sesión
seguía en vuelo, el `append_event` de ese turno salía rechazado como
obsoleto — un adorno de la barra lateral tumbando una respuesta real.
Reproducido a propósito: primer mensaje, 0.3s de espera, segundo mensaje →
antes fallaba, con el fix no.

- [x] Nueva tabla `session_titles` (migración `37a9f8f5a59d`), completamente
  aparte de la sesión de ADK: no comparte ningún candado con el turno de
  chat. `SqlSessionTitleRepository` (get/get_many/upsert/delete).
- [x] `TitleService` simplificado: ya no carga ni recarga la sesión de ADK
  en ningún punto, solo llama al repositorio. Menos código y sin la
  condición de carrera.
- [x] `GET /api/v1/sessions` lee los títulos en un solo round-trip
  (`get_many`), no uno por fila.
- [x] `DELETE /api/v1/sessions/{id}` limpia también la fila de
  `session_titles` — antes de esto no habría quedado huérfana en ADK
  (vivía en el propio estado de la sesión, que se borra con ella), así
  que hacía falta el borrado explícito para no dejar filas sueltas.
  Verificado.
- [x] 10 tests nuevos (`test_session_title_repository.py`,
  `test_title_service.py` con `ensure_title`).

Verificado en vivo contra el backend real: el escenario exacto que
reproducía el bug (mensaje + reintento a 0.3s) ya no falla — ambos turnos
`ok=True`, cero `StaleSessionError` en los logs. 173 tests de backend en
verde.

- [x] El aviso de "los modelos locales tardan más" del indicador de
  escritura salía siempre, incluso con Gemini seleccionado (un texto
  pensado para modelos locales en una llamada a una API en la nube no
  tiene sentido). Pasa a depender del proveedor real del modelo elegido,
  no de un texto fijo. Verificado en el navegador con los dos casos.

### Séptima ronda · todo el Ollama dentro de Docker, nada nativo

A pedido explícito del humano: quien descargue el repo no debería
depender de nada instalado fuera de Docker. Hasta esta ronda, `.env.example`
ya recomendaba el perfil `local-llm`, pero el `.env` real de esta máquina
seguía apuntando al Ollama nativo (`host.docker.internal:11434`) — dos
caminos coexistiendo, y el real (nativo) sin ser el documentado.

- [x] `.env` de esta máquina cambiado para usar exclusivamente el Ollama de
  Docker: `OLLAMA_API_BASE_CONTAINER=http://ollama:11434`,
  `COMPOSE_PROFILES=local-llm` (así `docker compose up -d`, sin ningún
  flag, ya incluye Ollama), `OLLAMA_PORT=11435` (el 11434 del host lo
  tiene el Ollama nativo, que sigue existiendo para otros proyectos pero
  este ya no lo toca). `AGENT_MODEL`/`FALLBACK_MODEL` pasaron a los tags
  fijos (`gemma4:12b`/`llama3.2:3b`) que el `docker-compose.yml` ya
  bajaba, en vez de los `:latest` de la instalación nativa.
- [x] `EMBEDDINGS_MODEL` de `embeddinggemma` a `embeddinggemma:300m` — el
  único cambio con costo real: `verify_embedding_model()` compara el
  string tal cual contra lo grabado en `kb_chunks`, así que hubo que
  volver a correr `scripts/ingest_kb.py` (71 fragmentos, contra el Ollama
  de Docker) antes de que el backend arrancara sin
  `EmbeddingModelMismatchError`.
- [x] `.env.example` y `docker-compose.yml` actualizados para que este sea
  el camino por defecto de cualquiera que clone el repo, no solo de esta
  máquina: `COMPOSE_PROFILES=local-llm` ya viene en la plantilla.
- [x] `MODEL_CHOICES` limpiado a solo Gemini (los de Ollama se descubren
  solos, declararlos a mano ya no tenía efecto desde la ronda del
  catálogo dinámico).

Verificado de punta a punta contra el Ollama de Docker exclusivamente:
`GET /api/v1/models` devuelve las 3 variantes instaladas ahí + Gemini,
`gemma4:12b` como default (coincide con `AGENT_MODEL`); una conversación
real con saludo (`guardar_lead`) y una pregunta técnica que dispara
`search_knowledge_base` con respuesta correcta; `ollama ps` dentro del
contenedor confirma `100% GPU` en los tres modelos con el mismo contexto
(32768) ya calibrado para la instalación nativa. 173 tests de backend en
verde (sin cambios, usan su propio entorno de test).

## F7 · `feature/feedback-evals` · P1

DoD: scores visibles en Langfuse; evalset corre.

- [x] `POST /feedback`
- [x] Evaluación post-ejecución en background
- [x] `EventsCompactionConfig` afinado
- [x] Evalset ADK

**F7 completo.** Solo queda F9 para cerrar el proyecto.

### `EventsCompactionConfig` afinado con conversaciones reales

Dos hallazgos reales al investigar antes de tocar el número, no una
adivinanza (leyendo `google/adk/apps/compaction.py`, verificado en vivo):

1. **Sin `summarizer` explícito, la compactación usaba el modelo grande del
   propio agente para resumir** (`agent.canonical_model`), en la misma
   llamada síncrona que cierra el turno — justo cuando la conversación ya es
   larga, el peor momento para sumarle otra llamada al modelo principal.
   `create_adk_app` ahora recibe el mismo modelo ligero que ya titula
   conversaciones (`GUARDRAIL_MODEL`) y se lo pasa explícito a
   `LlmEventSummarizer`. Un solo modelo de utilidad, no dos instancias.
2. **El número que dispara la compactación no es el `tokens_in` que muestra
   el panel dev.** Ese metric suma todas las llamadas al modelo de un turno
   (incluidas las de tool-calling); el disparador de ADK compara contra el
   `prompt_token_count` de la **última** llamada nada más. Confirmado
   inspeccionando una sesión real: un turno con `tokens_in=8249` (dos
   llamadas, 3817+4432) dejaba en 4432 el valor que ADK de verdad compara.

Con el umbral original (12000, puesto en F2 sin conversación real de por
medio) **la compactación no llegó a dispararse ni una vez** en una
conversación de 10 turnos con captura de lead y preguntas técnicas — el
crecimiento real ronda 300-700 tokens/turno con `gemma4:12b`. Bajado a
**6000**: dispararía alrededor del turno 8-10 de una conversación larga
(margen amplio frente a los 32768 de `OLLAMA_CONTEXT_LENGTH`), sin activarse
en los intercambios cortos de 2-5 turnos que son el caso común de este
asesor.

Verificado en vivo forzando el disparo con un umbral bajo (1500, temporal,
solo para la prueba): 3 compactaciones reales en la misma sesión, cero
errores y cero `StaleSessionError` (ADK ya maneja esa carrera de origen —
la misma que tuvimos que resolver a mano para `session_titles`, spec 06 §1
— con su propio try/except), y el resumen generado por el modelo ligero
conservó nombre, uso principal, etapa, qué tool se llamó y qué pregunta
quedó sin responder. Con 6000 en una conversación de 5 turnos, no se
disparó — consistente con el crecimiento medido, no una sorpresa.

1 test nuevo (`test_agent_factory.py`, fija que se usa el modelo ligero y no
el del agente). Suite completa: 191 tests, mypy y ruff limpios.

### Langfuse real configurado y `POST /feedback` + evaluación en background

El humano creó su propio proyecto de Langfuse (plan HIPAA, host distinto del
`cloud.langfuse.com` por defecto) y pasó las keys. Quedaron solo en `.env`
(nunca en `.env.example` ni comiteadas — verificado con `git check-ignore`).

- [x] Verificado end-to-end contra el Langfuse real, no asumido: un turno de
  verdad genera un trace consultable por la API pública de Langfuse
  (`GET /api/public/v2/observations`) con el árbol completo de spans
  (`chat.turn` → `invocation` → `agent_run` → `call_llm`). La API "legacy"
  de lectura de traces (`GET /api/public/traces/{id}`) está deprecada para
  cuentas nuevas — hay que usar la v2; documentado en el código.
- [x] `POST /api/v1/feedback`: tabla `feedback` (migración), repositorio,
  endpoint con el contrato exacto de spec 02, más el score `user-feedback`
  a Langfuse (`POST /api/public/scores`, también verificado en vivo:
  responde 200 y el score aparece consultable por `GET /api/public/v3/scores`
  con delay de unos minutos — la API de lectura de Langfuse lo advierte
  explícitamente).
- [x] Evaluación post-ejecución en background (`EvaluationService`): tras
  cada turno, si `EVAL_SAMPLE_RATE` lo elige, un juez con `EVAL_MODEL`
  (una sola llamada, no una por criterio) evalúa tono empático, brevedad,
  una sola pregunta y sin precios siempre, más fidelidad al RAG solo si el
  turno usó `search_knowledge_base`. Persiste en tabla `evaluations` y manda
  `quality.<criterio>` a Langfuse. Nunca bloquea `message.completed`: se
  agenda como `BackgroundTasks` una vez conocido el texto final, dentro del
  propio generador de `_stream` (no antes, a diferencia de `title_service`,
  porque necesita el resultado del turno, no solo el mensaje de entrada).
  Un turno reanudado por HITL (`chat/confirmations`) nunca se muestrea: no
  hay mensaje de usuario fresco que evaluar ahí.
- [x] Verificado en vivo contra el stack Docker + Ollama real con
  `EVAL_SAMPLE_RATE=1.0`: un turno real generó las 4 filas en `evaluations`
  con justificaciones coherentes del juez (`qwen3:4b-instruct`), y los
  scores llegaron a Langfuse.
- [x] `EVAL_SAMPLE_RATE` real de esta máquina en `1.0` para que la demo
  muestre evaluaciones en todos los turnos; el default de `.env.example`
  se queda en `0.0` (P1 opcional, cada turno muestreado es una llamada
  extra al modelo).
- [x] `tests/conftest.py`: `LANGFUSE_*` ahora se fuerzan a vacío en
  `TEST_ENV` — sin esto, con keys reales en el `.env` del desarrollador,
  toda la suite heredaba `telemetry_enabled=True` y command tests que
  asumían "sin Langfuse" se rompían (o peor, habrían llamado a la API real
  de Langfuse sin querer). Hallazgo real al configurar las keys, no
  hipotético.
- [x] 17 tests nuevos (feedback, telemetry/scores, evaluation_service,
  wiring de background). Suite completa: 190 tests, mypy y ruff limpios.

A pedido del humano: armar conversaciones on-topic y fuera de tema para
verificar que el agente no se sale de su guion, y correrlas de verdad contra
el Ollama real (no simuladas).

- [x] `backend/tests/evalset/luis.cases.json` — 7 conversaciones editables a
  mano sin tocar código: saludo, captura de lead, RAG (AT-06), y cuatro fuera
  de guion — pregunta totalmente ajena al dominio, intento de extraer el
  prompt/token interno (canary, spec 07), pedido de precio, y fondos
  colectivos/consorcios (exclusión explícita del reto).
- [x] Cada turno se valida con dos mecanismos reales, no un string fijo (un
  LLM no responde igual dos veces): `TrajectoryEvaluator` de ADK (tools
  llamadas, determinista) y un juez propio de una sola llamada a
  `EVAL_MODEL` (aquí Ollama, cero keys) que evalúa la respuesta contra
  reglas en español.
- [x] Marker `evalset` registrado (`pyproject.toml`), excluido de CI igual
  que `live`.

**Dos hallazgos verificando la API de ADK antes de usarla** (regla del
proyecto; detalle en `specs/notes/adk-api.md` §9):
1. El runner "oficial" de un `EvalSet` (`LocalEvalService`) arrastra
   `vertexai`/`pandas`/`nltk` en su cadena de imports — pesado y ajeno al
   "sin ninguna API key" del proyecto. Se usaron las clases de evaluación
   sueltas directamente en su lugar.
2. La única clase de rúbricas totalmente concreta de ADK
   (`RubricBasedFinalResponseQualityV1Evaluator`) exige "evidencia" de tools
   para dar una regla por cumplida, y marcó un saludo perfectamente correcto
   como fallido solo porque el turno no había llamado ninguna tool — está
   pensada para fidelidad a evidencia recuperada (RAG), no para reglas de
   tono/política. Se descartó por un juez propio de una sola llamada.

**Corriendo el evalset contra el modelo real salieron 3 casos que fallaban
al principio, los tres por el mismo motivo de fondo: el arnés asumía que
todo turno termina en texto, y eso no es cierto para dos desenlaces
legítimos del propio diseño del agente:**
- `precio-cotizacion`: el modelo interpretó "¿cuánto cuesta...?" como una
  cotización formal y propuso `solicitar_contacto_humano` (HITL) en vez de
  responder en texto — exactamente lo que spec 03 pide, no un fallo.
- `fondos-colectivos`: en corridas distintas del mismo mensaje, el modelo se
  comportó de tres formas distintas (escribió la tool como texto y quedó en
  blanco tras limpiarla, escribió la tool como texto con una respuesta de
  reemplazo de L4, o llamó la tool de verdad y disparó HITL) — la misma
  inconsistencia de tools de modelos pequeños ya documentada en ADR-003 #8,
  ahora vista en un caso concreto.
- `rag-suv-crossover`: una corrida agotó el presupuesto de tokens de salida
  (`FinishReason.MAX_TOKENS`) en un turno con tool + thinking; el backend lo
  tradujo a un `error` SSE retryable en vez de romperse (spec 07 funcionando
  como está diseñado) — no se reprodujo en corridas repetidas, documentado
  como hallazgo #9 en ADR-003 para quien lo retome.

El arnés ahora tolera explícitamente estos desenlaces por caso
(`accepts_hitl`/`tolerates_error` en el JSON), no los oculta: un caso que
dispare uno de estos sin haberlo declarado sigue fallando. **Verificado: los
7 casos pasan en una corrida completa contra el Ollama real** (`uv run
pytest tests/evalset -m evalset`, ~4 min). Suite normal sin regresiones: 173
tests en verde, mypy y ruff limpios.

Pendiente para quien retome esto: sumar casos al JSON es directo (no toca
código); `docs/pruebas-manuales.md` tiene el mismo espíritu para probar a
mano en el navegador, incluyendo el flujo de HITL completo (confirmar y
cancelar) que el evalset automático no cubre.

## F9 · `docs/release` · P0

DoD: checklist de entrega completo. **Parar antes del merge `develop → main`.**

- [x] README completo
- [x] Diagrama Mermaid, antes/después
- [x] Sync specs ↔ código
- [ ] PR `develop → main`
- [ ] Tag `v1.0.0`
- [ ] Video 5–7 min

### README y diagramas

`README.md` en la raíz (antes no existía ninguno): características, arquitectura
(diagrama Mermaid verificado con `@mermaid-js/mermaid-cli` antes de comitear —
un intento inicial con comillas escapadas dentro de una etiqueta no renderizaba,
corregido y re-verificado), comparación antes/después contra el baseline n8n
(dos diagramas + tabla de brechas cerradas, spec 00), quick start con Docker
(el camino sin API key como principal), estructura del proyecto, comandos,
tests y evaluación, e índice de documentación.

### Sync specs ↔ código: 7 desajustes reales encontrados, 6 arreglados directo, 1 resuelto con el humano

Auditoría dedicada (agente de exploración, no una relectura superficial) de
specs/03, 04, 05, 07, 10, 11 contra el código real. specs/01, 02, 06, 08, 09 ya
se habían mantenido al día durante las rondas de F6/F7 de esta sesión, así que
no se re-auditaron.

**Arreglados directo en la spec (sin tocar código, cero riesgo):**
- `search_knowledge_base`: la spec 03 decía `data` como array directo; el
  código envuelve en `{"resultados": [...]}`.
- `next_stage`: la spec 04 documentaba una firma `(current, lead, event)`; la
  real es `(current, lead)` — la etapa siguiente sale del propio `Lead`
  resultante, sin un `event` aparte.
- HITL: la spec 05 decía "pide confirmación explícita al usuario antes de
  ejecutar" — lo contrario de lo que hace el código (llama de inmediato, la
  tool nativa de ADK maneja la confirmación, ADR-002). La instrucción real ya
  lo dice bien; la spec se había quedado desactualizada.
- Nombres de placeholders de la instrucción: la spec 05 decía `{lead_json}`/
  `{canary_token}`; el código real usa `{ficha}`/`{canary}`.
- L2 (clasificador): la spec 07 lo listaba como capa activa. Sigue sin
  implementarse (P1) — esto ya lo decía `PROGRESS.md` desde F6, la spec 07
  nunca se había actualizado para reflejarlo. De paso, categorías
  `off_topic`/`abuse` (dependen de L2) marcadas como no emitidas todavía, y
  `GUARDRAIL_MODEL` aclarado como reutilizado por `TitleService`/compactación,
  no por ningún guardrail real.
- Spec 11: referencia colgante a un inexistente "spec 13" (era spec 10).

**Resuelto con el humano, no solo documentado:** `solo_mirando` (el modo
"solo estoy mirando" del baseline) nunca se activaba — la frase canned y la
lectura del flag existían, pero ningún código lo escribía (a diferencia de la
etapa, que sí se escribe desde `guardar_lead`). AT-05 tampoco tenía test
propio, así que nada lo había detectado. El humano pidió cerrarlo antes de la
entrega en vez de dejarlo documentado como límite conocido:

- [x] `guardar_lead` gana un campo opcional `solo_mirando: bool`, que puede ir
  solo (sin ningún otro campo, sin disparar `EMPTY_UPDATE`) y escribe
  `SOLO_MIRANDO_KEY` en el estado de sesión — mismo patrón que ya usaba la
  etapa.
- [x] Instrucción actualizada: el agente ahora sabe que debe llamar a
  `guardar_lead(solo_mirando=true)`, no solo decir la frase canned.
- [x] AT-05 real (`test_at_agent_core.py`) — tool call, frase exacta,
  `GET /sessions/{id}/lead` refleja `solo_mirando: true`, y el flag sigue
  activo (visible en la instrucción) en el turno siguiente.
- [x] **Verificado contra el modelo real, no solo el doble de test:** "por
  ahora solo estoy mirando" con `gemma4:12b` llamó la tool, dijo la frase
  exacta, y `GET /lead` devolvió `solo_mirando: true`.

### Repaso contra el PDF del reto y su rúbrica de evaluación

A pedido del humano, antes de la parada obligatoria de `develop → main` se
releyó el enunciado completo (rúbrica incluida) contra el estado real del
código, no solo contra los specs. Dos ajustes:

- [x] **README ganó una justificación del framework escrita directo, no solo
  enlazada.** El enunciado pide "justificación técnica del framework
  agéntico seleccionado" *en* el README — antes solo había un link a
  `ADR-001-framework.md`. Se agregó un párrafo propio (§ "Por qué Google
  ADK").
- [x] **Diagrama nuevo: "Flujo de un turno"**, con memoria, las 3 tools, HITL
  y guardrails como nodos explícitos — el enunciado pide el diagrama
  "especificando memoria, tools, HITL y guardrails" y el diagrama de
  componentes original no los etiquetaba como pasos de un flujo. Verificado
  con `mermaid-cli` como los otros tres.
- [x] **Feedback del usuario con UI real, no solo el endpoint.** La rúbrica
  (20%, "Implementación del Harness") pide explícitamente "captura de
  feedback del usuario" como resultado esperado — más fuerte que el "opcional"
  del cuerpo del enunciado, que habla del feedback loop de *evaluación*, no
  del de usuario. `MessageList` ganó botones 👍/👎 bajo la última respuesta
  del agente (`onFeedback`, `api.sendFeedback` nuevo en `client.ts`,
  `sendFeedback` en `useChat`). Verificado en el navegador contra el stack
  real: la fila queda en `feedback` y el score llega a Langfuse — un primer
  intento de verificación pareció fallar (la fila no aparecía) porque el
  script de prueba cerraba el navegador antes de que la llamada a Langfuse
  (awaited dentro del propio endpoint) terminara; no es un bug de la app.
- [x] `.gitignore` ganó `*.pdf`: el enunciado del reto vivía sin trackear en
  la raíz del repo — un `git add -A` lo habría comiteado, metiendo el nombre
  de la empresa del proceso de selección al historial.

Resto del enunciado, verificado sin cambios de código: persistencia SQL ✅,
sesiones concurrentes sin fuga (AT-19) ✅, tipado estricto en ambos lados
(mypy strict + TS strict) ✅, config vía variables de entorno ✅, rama por
fase con merge commits ✅, specs cubriendo contratos de API/tools,
transiciones de estado y AT/guardrails ✅.

Frontend: typecheck, build y 22 tests de vitest limpios.

Suite completa: 192 tests, mypy y ruff limpios.

### Segundo repaso contra el PDF, a pedido del humano

Releído el PDF completo (MVP, entregables y rúbrica) de nuevo, no solo la
memoria de la ronda anterior. Un hallazgo real:

- [x] **"Asesor general, no asociado a marcas específicas ni sistemas de
  fondos colectivos" nunca estaba en la instrucción del agente** — es el
  primer punto del MVP en el enunciado, palabra por palabra, y ni
  `instruction.py` ni la spec 05 lo mencionaban. El comportamiento correcto
  salía porque la KB no tiene datos de marcas ni de ese producto (regla
  implícita, no diseñada) — funcionaba, pero por accidente de qué hay en la
  KB, no por una regla del agente. Se agregó la regla explícita al ROL de
  la instrucción y a la spec 05 (fila 11 de la tabla de cambios).
  Verificado contra el modelo real: los casos del evalset
  `saludo-generico` y `fondos-colectivos` siguen pasando sin cambios de
  comportamiento. 192 tests, mypy y ruff limpios.

Verificado también, sin encontrar nada nuevo que cambiar: las spans de
`execute_tool` (una por tool llamada, ej. `solicitar_contacto_humano`)
aparecen en Langfuse junto a `call_llm`/`agent_run`/`invocation` — la
"visualización de tool calls" de la rúbrica de Observabilidad (10%) ya
estaba cubierta por la instrumentación propia de ADK, sin código nuestro
de más. Confirmado contra el Langfuse real vía `GET
/api/public/v2/observations`, no solo asumido.

**Único bloqueante real que queda:** no existe repositorio remoto en
GitHub/GitLab. Es un entregable explícito de la rúbrica ("Repositorio de
Código... se valorará el uso correcto de la gestión de ramificación en
Git") y el único canal de entrega es el link público por correo — sin
esto no hay nada que evaluar. Todo el historial local (`main`, `develop`,
merge commits por fase) ya está listo para empujarlo tal cual en cuanto
exista el remoto.
