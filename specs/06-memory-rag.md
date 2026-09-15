# 06 · Memoria, sesiones y RAG

## 1. Identidad y sesiones

- `user_id`: UUID anónimo generado por el **frontend** en el primer uso (persistido en `localStorage`), enviado como header `X-User-Id` en cada request. No hay login: es el reemplazo del `sessionKey` inestable del baseline (brecha #2, spec 00).
- `session_id`: creado por `POST /api/v1/sessions`, asociado al `user_id` que lo creó. Toda operación sobre una sesión (`GET messages`, `GET lead`, `chat/stream`, `chat/confirmations`) valida `session.user_id == X-User-Id` → 404 si no coincide (nunca 403, para no confirmar existencia a otro usuario).
- Memoria de conversación: `DatabaseSessionService` de ADK sobre PostgreSQL (`postgresql+asyncpg://`). Alembic y `scripts/ingest_kb.py` usan un DSN síncrono aparte (gotcha #2 de la sección 19 del prompt maestro) — mismo host/DB, driver distinto.
- Etapa del diálogo y banderas (`solo_mirando`, `etapa_previa`) viven en el estado de sesión ADK (session state), no en una tabla nueva.
- Datos del lead: persistidos **por usuario** en la tabla `leads` (PK `user_id`), no por sesión. **Decisión de F2:** la tabla es la única fuente de verdad y el proveedor de instrucción la consulta en cada turno; el lead **no** se duplica en el estado con prefijo `user:` de ADK, para no tener dos copias que se puedan desincronizar. El prefijo `user:` existe y está verificado (`specs/notes/adk-api.md` §4) y queda disponible si alguna bandera necesita alcance de usuario. Así, quien abre una sesión nueva es saludado por su nombre sin repetir el descubrimiento (AT-02).

## 2. Control de tamaño del historial

- `EventsCompactionConfig` de ADK: umbral por tokens + N eventos recientes intactos (valores exactos por env: `MEMORY_COMPACTION_TOKEN_THRESHOLD`, `MEMORY_COMPACTION_KEEP_RECENT`).
- **Prohibido** recortar `contents` a mano en callbacks propios: puede romper las firmas de pensamiento (`thought_signature`) que Gemini 3 exige en function calling, causando errores 400 en el siguiente turno con tools.
- Como la compactación puede resumir mensajes antiguos, el idioma y el nombre del usuario **no dependen de que el resumen los conserve**: van inyectados en la instrucción desde el estado de sesión/lead en cada turno (spec 05 §1).

## 3. Test de aislamiento (obligatorio)

Dos o más sesiones concurrentes de usuarios distintos, lanzadas con `asyncio.gather`, no deben cruzar nombre, lead ni historial entre sí. Es un test de integración (`backend/tests/integration/`) marcado como bloqueante para el DoD de F2 — reproduce directamente la brecha #2 del baseline (AT correspondiente en spec 09).

## 4. RAG

- Motor: pgvector en el mismo Postgres. Columna `embedding vector(768)`, índice HNSW, distancia coseno.
- Puerto `Embeddings` (spec 01, 11): Gemini (`gemini-embedding-001` o `gemini-embedding-2` truncado/proyectado a 768 dims) u Ollama (`embeddinggemma`, 768 dims nativas).
- Tabla `kb_chunks`: `id, chunk_id, title, categoria, source, content, embedding, embedding_model, content_hash, created_at`.
- **Ingesta** (`backend/scripts/ingest_kb.py`, `make ingest-kb`): lee `kb/*.md` (frontmatter `title`, `categoria`), chunkea por encabezados (~400–700 tokens, solapamiento corto), calcula `content_hash` por chunk — **idempotente**: si el hash no cambió, no reinserta ni recalcula embedding.
- **Chequeo de arranque:** si `embedding_model` almacenado en `kb_chunks` difiere del configurado (`EMBEDDINGS_PROVIDER`/modelo), la app falla al arrancar con un mensaje claro pidiendo re-ingesta — son espacios vectoriales distintos y no son comparables por coseno.
- **Retrieval:** `search_knowledge_base` (spec 03) filtra opcionalmente por `categoria`, ordena por score de coseno, aplica `RAG_MIN_SCORE` (env) como piso de aceptación → si no se alcanza, `no_results`.
- Contenido de la KB: spec dedicada en `00-master-build.md` §12 (15–18 markdown genéricos, sin marcas ni precios).

## 5. Variables de entorno relevantes

`EMBEDDINGS_PROVIDER`, `EMBEDDINGS_MODEL`, `RAG_MIN_SCORE`, `MEMORY_COMPACTION_TOKEN_THRESHOLD`, `MEMORY_COMPACTION_KEEP_RECENT` — documentadas con valores por defecto y ejemplo en `.env.example` (F1).
