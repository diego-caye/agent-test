# 06 · Memoria, sesiones y RAG

## 1. Identidad y sesiones

- `user_id`: UUID anónimo generado por el **frontend** en el primer uso (persistido en `localStorage`), enviado como header `X-User-Id` en cada request. No hay login: es el reemplazo del `sessionKey` inestable del baseline (brecha #2, spec 00).
- `session_id`: creado por `POST /api/v1/sessions`, asociado al `user_id` que lo creó. Toda operación sobre una sesión (`GET messages`, `GET lead`, `chat/stream`, `chat/confirmations`) valida `session.user_id == X-User-Id` → 404 si no coincide (nunca 403, para no confirmar existencia a otro usuario).
- Memoria de conversación: `DatabaseSessionService` de ADK sobre PostgreSQL (`postgresql+asyncpg://`). Alembic y `scripts/ingest_kb.py` usan un DSN síncrono aparte (gotcha #2 de la sección 19 del prompt maestro) — mismo host/DB, driver distinto.
- Etapa del diálogo y banderas (`solo_mirando`, `etapa_previa`) viven en el estado de sesión ADK (session state), no en una tabla nueva.
- Datos del lead: persistidos **por usuario** en la tabla `leads` (PK `user_id`), no por sesión. **Decisión de F2:** la tabla es la única fuente de verdad y el proveedor de instrucción la consulta en cada turno; el lead **no** se duplica en el estado con prefijo `user:` de ADK, para no tener dos copias que se puedan desincronizar. El prefijo `user:` existe y está verificado (`specs/notes/adk-api.md` §4) y queda disponible si alguna bandera necesita alcance de usuario. Así, quien abre una sesión nueva es saludado por su nombre sin repetir el descubrimiento (AT-02).
- **Título de la conversación:** tabla propia `session_titles` (PK `session_id`), no estado de sesión ADK. Se probó con `append_event` + `state_delta` primero y se encontró en producción un problema real: el título se genera en segundo plano (`TitleService`, spec 08) y su escritura competía por el mismo lock optimista de ADK que el turno de chat activo — si el título se guardaba mientras un turno siguiente en la misma sesión seguía en vuelo (típicamente un mensaje enviado rápido después del primero, o un reintento), el `append_event` del propio turno salía rechazado con `StaleSessionError`, tumbando una respuesta real por un adorno de la barra lateral. Una tabla SQL independiente no comparte ese candado con nada: `SqlSessionTitleRepository` (upsert/get/get_many/delete), sin tocar la sesión de ADK en ningún punto.

## 2. Control de tamaño del historial

- `EventsCompactionConfig` de ADK: umbral por tokens + N eventos recientes intactos (valores exactos por env: `MEMORY_COMPACTION_TOKEN_THRESHOLD`, `MEMORY_COMPACTION_KEEP_RECENT`).
- **Prohibido** recortar `contents` a mano en callbacks propios: puede romper las firmas de pensamiento (`thought_signature`) que Gemini 3 exige en function calling, causando errores 400 en el siguiente turno con tools.
- Como la compactación puede resumir mensajes antiguos, el idioma y el nombre del usuario **no dependen de que el resumen los conserve**: van inyectados en la instrucción desde el estado de sesión/lead en cada turno (spec 05 §1).
- **Resumidor explícito, no el default de ADK.** `EventsCompactionConfig.summarizer` es opcional; si se omite, ADK usa por defecto `agent.canonical_model` — el modelo grande del propio agente — para escribir el resumen, en la misma llamada síncrona que cierra el turno (verificado leyendo `google/adk/apps/compaction.py`). `create_adk_app` (`agent/factory.py`) le pasa en su lugar el mismo modelo ligero que ya titula conversaciones (`GUARDRAIL_MODEL`): resumir no es tarea para el modelo principal, y sumarle otra llamada justo cuando la conversación ya es larga —el peor momento— sería innecesario.
- **Afinado con conversaciones reales (F7), no en abstracto:**
  - El número que dispara la compactación **no es** la suma de tokens que se muestra en el panel dev (`tokens_in` sí acumula todas las llamadas al modelo de un turno, incluidas las de tool-calling). El disparador de ADK mira `usage_metadata.prompt_token_count` de la **última** llamada del turno más reciente — un solo número, no la suma. Confirmado inspeccionando sesiones reales: un turno con `tokens_in=8249` (dos llamadas: 3817 + 4432) dejaba el valor que de verdad compara ADK en 4432.
  - Con el umbral original (12000, heredado de F2 sin conversación real de por medio) **la compactación nunca llegó a dispararse** en una conversación de 10 turnos con captura de lead y dos preguntas técnicas — el crecimiento real es de ~300-700 tokens por turno con `gemma4:12b`, así que 12000 solo se alcanzaría muy entrada una conversación larga, si es que se alcanza.
  - Bajado a **6000**: en la misma clase de conversación dispararía alrededor del turno 8-10 (con margen amplio frente a los 32768 de `OLLAMA_CONTEXT_LENGTH`), sin activarse en los intercambios cortos de 2-5 turnos que son el caso común de este asesor.
  - Verificado en vivo forzando el disparo con un umbral bajo (1500, temporal, solo para la prueba): la compactación corrió sin errores ni `StaleSessionError`, y el resumen generado por el modelo ligero conservó lo que importa (nombre, uso principal, etapa, qué tool se llamó, qué pregunta quedó sin responder) — no hubo pérdida de contexto relevante para el anti-loop de spec 03/04.

## 3. Test de aislamiento (obligatorio)

Dos o más sesiones concurrentes de usuarios distintos, lanzadas con `asyncio.gather`, no deben cruzar nombre, lead ni historial entre sí. Es un test de integración (`backend/tests/integration/`) marcado como bloqueante para el DoD de F2 — reproduce directamente la brecha #2 del baseline (AT correspondiente en spec 09).

## 4. RAG

- Motor: pgvector en el mismo Postgres. Columna `embedding vector(768)`, índice HNSW, distancia coseno.
- Puerto `Embeddings` (spec 01, 11): Gemini (`gemini-embedding-001` o `gemini-embedding-2` truncado/proyectado a 768 dims) u Ollama (`embeddinggemma`, 768 dims nativas).
- Tabla `kb_chunks`: `id, chunk_id, title, categoria, source, content, embedding, embedding_model, content_hash, created_at`.
- **Ingesta** (`backend/scripts/ingest_kb.py`, `make ingest-kb` o `docker compose exec backend uv run python scripts/ingest_kb.py` — `scripts/` y `kb/` se montan en el backend justo para esto, no se copian a la imagen): lee `kb/*.md` (frontmatter `title`, `categoria`), chunkea por encabezados (~400–700 tokens, solapamiento corto), calcula `content_hash` por chunk — **idempotente**: si el hash no cambió, no reinserta ni recalcula embedding.
- **Chequeo de arranque:** si `embedding_model` almacenado en `kb_chunks` difiere del configurado (`EMBEDDINGS_PROVIDER`/modelo), la app falla al arrancar con un mensaje claro pidiendo re-ingesta — son espacios vectoriales distintos y no son comparables por coseno.
- **Retrieval:** `search_knowledge_base` (spec 03) filtra opcionalmente por `categoria`, ordena por score de coseno, aplica `RAG_MIN_SCORE` (env) como piso de aceptación → si no se alcanza, `no_results`.
- Contenido de la KB: spec dedicada en `00-master-build.md` §12 (15–18 markdown genéricos, sin marcas ni precios).

## 5. Variables de entorno relevantes

`EMBEDDINGS_PROVIDER`, `EMBEDDINGS_MODEL`, `RAG_MIN_SCORE`, `MEMORY_COMPACTION_TOKEN_THRESHOLD`, `MEMORY_COMPACTION_KEEP_RECENT` — documentadas con valores por defecto y ejemplo en `.env.example` (F1).
