# 02 · Contrato de API

Base path: `/api/v1`. Auth de usuario: header `X-User-Id` (UUID anónimo generado por el frontend, spec 06). Auth admin: header `Authorization: Bearer <ADMIN_TOKEN>` en endpoints marcados `(admin)`. CORS restringido al origen del frontend (`FRONTEND_ORIGIN`). Errores HTTP: cuerpo `{code, message, retryable}`.

## 1. Endpoints

### `POST /api/v1/sessions`
Crea una sesión ADK para el `user_id` del header.
- Body: `{}` (opcional `{"label": str}` a futuro, no en P0)
- 200: `{"session_id": str}`
- 401 si falta `X-User-Id`

### `GET /api/v1/sessions`
Lista sesiones del usuario del header, más recientes primero.
- 200: `[{"titulo": str | null, "session_id", "last_update_time", "etapa"}]`
- `titulo` es un resumen de 3–6 palabras del primer mensaje, generado en segundo plano por `GUARDRAIL_MODEL` (el modelo ligero) y guardado en el estado de sesión bajo la clave `titulo`. Es `null` mientras no se haya generado: el frontend muestra "Conversación nueva". Nunca bloquea ni hace fallar el turno; si el modelo no da nada usable se cae al propio mensaje del usuario recortado a 48 caracteres.

### `DELETE /api/v1/sessions/{id}`
Borra una conversación del usuario del header, con sus eventos.
- 204 sin cuerpo
- 404 si la sesión no existe o no pertenece al `user_id` (se comprueba la propiedad antes de borrar, para no revelar la existencia de sesiones ajenas)
- El lead **no** se borra: vive a nivel usuario, no de sesión (spec 06 §1)

### `GET /api/v1/sessions/{id}/messages`
Historial de una sesión.
- 200: `[{"role": "user"|"agent", "content", "created_at"}]`
- 404 si la sesión no existe o no pertenece al `user_id` del header

### `GET /api/v1/sessions/{id}/lead`
Ficha actual del lead asociado al usuario dueño de la sesión.
- 200: `{"lead": {...campos de guardar_lead...} | null, "etapa": str, "solo_mirando": bool}`
- 404 si la sesión no existe o no pertenece al `user_id`

### `POST /api/v1/chat/stream` (SSE)
Envía un mensaje y transmite la respuesta en streaming.
- Body: `{"session_id": str, "message": str (1–2000), "model_id"?: str}`
- `model_id` es un `id` del catálogo de `GET /api/v1/models`; si se omite, el primero del catálogo. El modelo se elige **por turno**, no por sesión: la conversación es la misma y el historial se conserva al cambiar, porque la sesión vive en `DatabaseSessionService` y no en el modelo. 400 `unknown_model` si el `id` no existe
- 404 si la sesión no pertenece al `user_id` del header
- Respuesta: `text/event-stream`, eventos definidos en §2
- Si hay un fault injection activo (`X-Debug-Fault`, solo `APP_ENV=dev` y `ENABLE_FAULT_INJECTION=true`), fuerza el camino de error correspondiente (spec 07)

### `POST /api/v1/chat/confirmations` (SSE)
Responde una confirmación HITL pendiente y reanuda el stream del turno.
- Body: `{"session_id": str, "confirmation_id": str, "approved": bool, "comment"?: str, "model_id"?: str}`
- Conviene reanudar con el mismo `model_id` que pidió la confirmación: cambiarlo a mitad de un turno pausado mezcla dos modelos en una sola respuesta
- Respuesta: `text/event-stream`, continúa la misma secuencia de eventos que `chat/stream`
- 404 si `confirmation_id` no existe o ya fue resuelto

### `GET /api/v1/models`
Catálogo del selector de modelos, en el orden de `MODEL_CHOICES`.
- 200: `[{"id", "label", "provider": "gemini"|"ollama", "model", "available": bool, "is_default": bool}]`
- `available` es false cuando el proveedor de esa opción no está configurado (Gemini sin `GOOGLE_API_KEY`). La interfaz las muestra deshabilitadas en vez de ocultarlas, para que se vea qué hay y por qué no se puede usar
- Sin `MODEL_CHOICES` el catálogo tiene una sola entrada, la de `AGENT_MODEL`, y el selector se oculta
- No requiere `X-User-Id`: es configuración del despliegue, no del usuario

### `POST /api/v1/feedback`
- Body: `{"session_id": str, "trace_id": str, "score": 1 | -1, "comment"?: str (≤500)}`
- 200: `{"ok": true}`
- 404 si la sesión no pertenece al `user_id`

### `GET /api/v1/handoffs?status=` (admin)
- Query `status?: OPEN | IN_PROGRESS | CLOSED`
- 200: `[{"id", "session_id", "user_id", "motivo", "resumen_requerimiento", "canal_preferido", "urgencia", "status", "created_at"}]`

### `PATCH /api/v1/handoffs/{id}` (admin)
- Body: `{"status": "IN_PROGRESS" | "CLOSED"}`
- 200: handoff actualizado
- 404 si no existe; 409 si la transición de estado no es válida (spec 03 §2)

### `GET /healthz`
- 200: `{"status": "ok"}` sin dependencias externas (liveness)

### `GET /readyz`
- 200: `{"status": "ok", "db": "ok", "llm": "ok"}` — verifica conexión a Postgres y que el provider LLM configurado responde a un ping barato
- 503 si alguna dependencia falla, con el detalle en el cuerpo

## 2. Eventos SSE (`chat/stream` y `chat/confirmations`)

Formato `event: <nombre>\ndata: <json>\n\n`.

| Evento | Payload | Cuándo |
|---|---|---|
| `message.delta` | `{"delta": str}` | Texto del agente. **Se emite una sola vez por turno, con la respuesta completa** (ver §4) |
| `message.completed` | `{"message_id", "trace_id", "latency_ms", "tokens_in", "tokens_out", "model"}` | Fin del turno (éxito) |
| `tool.started` | `{"name": str}` | Antes de ejecutar una tool |
| `tool.finished` | `{"name", "status", "duration_ms"}` | Después de ejecutar una tool |
| `lead.updated` | `{"lead": {...}, "etapa": str}` | Tras `guardar_lead` o cambio de etapa |
| `hitl.confirmation_required` | `{"confirmation_id", "motivo", "resumen", "canal_preferido", "urgencia"}` | El agente propone `solicitar_contacto_humano` y espera confirmación |
| `handoff.created` | `{"handoff_id", "ticket", "motivo", "status", "ya_existia"}` | La derivación se confirmó y el handoff quedó abierto. `ya_existia: true` cuando la idempotencia devolvió uno ya abierto (spec 03 §3) |
| `guardrail.triggered` | `{"layer": "L1"\|"L2"\|"L4", "category": str}` | Un guardrail bloqueó o modificó la respuesta |
| `error` | `{"code", "message", "retryable": bool}` | Fallo de tool, modelo, RAG o DB (spec 07) |

Un turno normal: `tool.started/finished`* → `message.delta`* → `lead.updated`? → `message.completed`. Un turno con HITL pendiente emite `hitl.confirmation_required` y cierra el stream; se reanuda con `POST /chat/confirmations`, que emite la misma secuencia (más `handoff.created` si se aprobó).

## 4. Por qué el texto no se transmite token a token (decidido en F6)

El diseño original enviaba un `message.delta` por cada fragmento del modelo. Al implementar L4 (filtro de salida, spec 07) resultó incompatible: **una vez transmitido un delta, no hay forma de retirarlo del cliente**, así que un precio o una fuga del canary ya habría llegado al usuario cuando L4 lo detecta sobre la respuesta completa.

Decisión: el backend acumula el texto del modelo y emite **un solo `message.delta`** con la respuesta ya revisada. Se pierde la escritura token a token; se gana que nada sin filtrar llegue nunca al navegador.

La sensación de tiempo real se mantiene con lo que sí se transmite en vivo: `tool.started` y `tool.finished` (chips de actividad), `lead.updated`, `hitl.confirmation_required` y `guardrail.triggered`. El contrato del evento no cambia, así que un cliente que maneje varios deltas sigue funcionando.

Alternativa descartada: transmitir en crudo y emitir un evento de reemplazo al detectar la fuga. Se descartó porque el texto inseguro llega igual a la pantalla, aunque sea un instante, y con el canary eso ya es la fuga que se quería evitar.

## 3. Errores HTTP comunes

| Code | HTTP | Cuándo |
|---|---|---|
| `UNAUTHORIZED` | 401 | Falta `X-User-Id` o `ADMIN_TOKEN` inválido |
| `NOT_FOUND` | 404 | Recurso inexistente o no perteneciente al usuario |
| `VALIDATION_ERROR` | 422 | Body inválido (FastAPI/Pydantic) |
| `CONFLICT` | 409 | Transición de estado inválida (handoff) |
| `UPSTREAM_UNAVAILABLE` | 503 | DB o LLM caídos (`retryable: true`) |
