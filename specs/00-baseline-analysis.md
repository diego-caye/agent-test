# 00 · Análisis del baseline n8n

> Fuente: `.local/baseline_n8n.json` (workflow "Asesor Automotriz Virtual - Baseline Challenge"). Este archivo no se versiona; este documento parafrasea su contenido para que el repo público no dependa de él.

## 1. Mapa de nodos n8n → componente ADK

| Nodo n8n | Tipo | Componente ADK / propio |
|---|---|---|
| `When chat message received` | `chatTrigger` | `POST /api/v1/chat/stream` (FastAPI + SSE) |
| `Postgres Chat Memory` | `memoryPostgresChat` (`sessionKey` custom, tabla `workflow.auto_chat_histories`) | `DatabaseSessionService` de ADK sobre Postgres (spec 06) |
| `Google Vertex Chat Model` | `lmChatGoogleVertex`, `gemini-1.5-pro`, `temperature 0.2` | Puerto `LlmProvider` → adaptador Gemini, modelo por `AGENT_MODEL` (spec 11) |
| `guardar_lead` | `toolCode` (JS inline) | Tool `guardar_lead`, adaptador delgado sobre `LeadService` (spec 03) |
| `solicitar_contacto_humano` | `toolCode` (JS inline, ticket con `Math.random`) | Tool `solicitar_contacto_humano` + `HandoffService` + confirmación de tools ADK (spec 03, 04, ADR-002) |
| `base_conocimientos_autos` | `toolVectorStore` | Tool `search_knowledge_base` (spec 03) |
| `PGVector Auto Knowledge` | `vectorStorePGVector`, tabla `workflow.rag_auto_knowledge` | pgvector en el mismo Postgres, tabla `kb_chunks` (spec 06) |
| `Google Vertex Embeddings` | `embeddingsGoogleVertex`, `text-embedding-004` | Puerto `Embeddings` → adaptador Gemini, `gemini-embedding-001`/`-2` (spec 11) |
| `AGENTE_LUIS` | `agent` (system message completo, `retryOnFail`, `maxTries: 3`, `waitBetweenTries: 3000`) | `Agent` ADK "Luis" (spec 05) + backoff exponencial en el adaptador LLM (spec 07) |

## 2. Instrucción del baseline (resumen fiel)

Secciones del `systemMessage` original: ROL, VOZ, SALUDO Y APERTURA (dos variantes: sin/con nombre), GUARDAR DATOS DEL CONTACTO, CONSULTA DE INFORMACIÓN, DERIVACIÓN A ESPECIALISTA, EL ARTE DE NO HOSTIGAR Y CONTINUIDAD (una pregunta por turno, anti-loop, "solo estoy mirando"), LÍMITES Y SEGURIDAD (fuera de tópico, jailbreak).

Frases canned que se conservan literalmente (fuente de verdad para spec 05 y 07):
- Saludo sin nombre: *"Hola 👋 Soy Luis, tu asesor automotriz. ¿Con quién tengo el gusto?"*
- Saludo con nombre: *"¡Hola [Nombre]! 👋 ¿En qué te puedo asesorar hoy con tu próximo auto?"*
- Sin datos en KB: *"Por el momento no cuento con el detalle técnico exacto sobre ese modelo, pero puedo anotarlo para que un especialista te dé el dato preciso 😊"*
- "Solo estoy mirando": *"¡Perfecto! Aquí estoy si quieres comparar modelos o resolver dudas 😊"*
- Fuera de tópico: *"Mi especialidad es ayudarte a encontrar el auto ideal y resolver dudas sobre vehículos 😊 Cuéntame si te puedo guiar con algún modelo."*
- Jailbreak / inyección: *"No puedo realizar esa acción 😊 ¿En qué te ayudo respecto a tu búsqueda de auto?"*

Reglas de negocio a preservar: una pregunta por turno, anti-loop ("si un dato ya fue entregado, no lo vuelvas a pedir"), no precios/cotizaciones/stock, derivación ante test drive / compra inmediata / disconformidad / fuera de alcance.

## 3. Brechas verificadas contra el JSON

1. **Modelos descontinuados.** `modelName: "gemini-1.5-pro"` (Chat Model) y `modelName: "text-embedding-004"` (Embeddings) ya no están disponibles como IDs vigentes de la API de Gemini. → los IDs se fijan solo por env (`AGENT_MODEL`, `EMBEDDINGS` en spec 11) y se verifican contra la documentación oficial antes de cada fase.
2. **`sessionKey` con fallback inseguro.** `"={{ $json.sessionId || 'session_default' }}"`: si el frontend no manda `sessionId`, todas las conversaciones sin id comparten la misma fila de memoria — fuga de historial entre usuarios. → sesiones creadas explícitamente por el backend (`POST /api/v1/sessions`), sin fallback compartido (spec 02, 06).
3. **Tools de código sin contrato.** Los `toolCode` de `guardar_lead` y `solicitar_contacto_humano` no declaran input schema (n8n infiere los parámetros del LLM sin validación), no persisten nada real (el "guardado" es un `JSON.stringify` en memoria del propio nodo) y el ticket se genera con `"TICK-" + Math.floor(Math.random() * 90000 + 10000)` — no persistente, colisionable, no auditable. → Pydantic schemas explícitos, persistencia real en `leads`/`handoffs`, ids por PK de base de datos (spec 03).
4. **Inconsistencia de campos entre prompt y código.** El `systemMessage` le pide al modelo guardar `canal_contacto`, pero el código de `guardar_lead` lee `session_id`, `nombre`, `tipo_vehiculo_interes`, `uso_principal`, `etapa` — `canal_contacto` no se usa en ningún lado. Además `session_id` (un identificador técnico) queda expuesto como argumento que el LLM debe rellenar. → `session_id`/`user_id` nunca son argumentos del LLM: llegan por `ToolContext` (spec 03).
5. **Estado no inyectado.** El prompt dice *"Si el contexto NO tiene Nombre"* / *"Si el contexto YA tiene Nombre"*, pero no hay ningún nodo que arme ese contexto antes del agente — el LLM debe inferirlo del historial crudo, lo que rompe con memoria compactada o entre sesiones. → la ficha del lead y la etapa se inyectan explícitamente en la instrucción en cada turno (spec 05, 06).
6. **HITL sin ciclo real.** `solicitar_contacto_humano` termina en el `JSON.stringify` del propio código; no hay pausa del workflow, cola humana, ni confirmación del usuario antes de ejecutar — el "ticket" nunca llega a nadie. → confirmación de tools ADK + tabla `handoffs` con estados y endpoints admin (spec 03, 04, ADR-002).
7. **Guardrails solo por prompt.** Las instrucciones de LÍMITES Y SEGURIDAD dependen enteramente de que el modelo las respete; no hay capa determinista, clasificador, ni filtro de salida — vulnerable a variaciones de la instrucción de jailbreak que el modelo no reconozca. → L1–L4 (spec 07).
8. **RAG y memoria sin gobierno.** `PGVector Auto Knowledge` no tiene proceso de ingesta visible, umbral de similitud, ni metadatos de fuente; `Postgres Chat Memory` no tiene límite de tokens ni compactación; no hay trazas, spans ni métricas de latencia/tokens en ningún nodo. → ingesta idempotente + `RAG_MIN_SCORE` (spec 06), `EventsCompactionConfig` (spec 06), OTel + Langfuse (spec 08).
9. **`temperature: 0.2`.** Configurado en el nodo `lmChatGoogleVertex`. No aplica igual a la familia Gemini 3.x: Google recomienda dejar el default (1.0); valores bajos pueden inducir loops de tool-calling. Desviación intencional documentada, no un bug a replicar (spec 05).

## 4. Qué se conserva sin cambios de fondo

Rol y voz de "Luis", las seis frases canned de la sección 2, las tres tools (mismo propósito, contrato nuevo), la fuente de conocimiento (documentación automotriz general vía RAG), y la política de no dar precios/cotizaciones/stock.
