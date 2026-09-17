# 03 · Tools del agente

Las tools son adaptadores delgados en `agent/tools/`: parsean argumentos con Pydantic, llaman a un servicio de `application/`, y devuelven el envelope común. `session_id` y `user_id` se leen del `ToolContext` de ADK — **nunca** son parámetros que el LLM deba rellenar (brecha #4 del baseline, spec 00).

## 1. Envelope común

```json
{"status": "ok" | "no_results" | "error", "data": {...}, "error": {"code": str, "message": str, "retryable": bool}}
```
`data` presente si `status="ok"`/`"no_results"`; `error` presente si `status="error"`. Un error de validación Pydantic se captura y se convierte en `status="error"`, `error.code="VALIDATION_ERROR"` — el agente lo lee y pide el dato de forma natural, nunca expone el traceback.

## 2. `guardar_lead`

Upsert parcial de la ficha del lead del `user_id` actual (no de la sesión: el lead vive a nivel usuario, spec 06).

**Input**
| Campo | Tipo | Regla |
|---|---|---|
| `nombre` | `str?` | 1–80 caracteres |
| `telefono` | `str?` | normalizado a 9 dígitos Perú o E.164 |
| `email` | `EmailStr?` | |
| `canal_preferido` | `enum?` | `WHATSAPP \| LLAMADA \| EMAIL \| CHAT` |
| `consentimiento_contacto` | `bool?` | obligatorio `true` si `telefono` o `email` vienen en la misma llamada; si no → `error.code=CONSENT_REQUIRED` y no se persiste el dato de contacto |
| `uso_principal` | `enum?` | `CIUDAD \| TRABAJO \| FAMILIA \| VIAJES \| MIXTO` |
| `tipo_vehiculo_interes` | `enum?` | `SUV \| SEDAN \| HATCHBACK \| PICKUP \| VAN \| CROSSOVER \| OTRO` |
| `motorizacion_interes` | `enum?` | `GASOLINA \| DIESEL \| HIBRIDO \| ELECTRICO \| GLP_GNV \| NO_DEFINIDO` |
| `nivel_interes` | `enum?` | `BAJO \| MEDIO \| ALTO`, lo infiere el LLM de señales conversacionales |
| `solo_mirando` | `bool?` | `true` la primera vez que el usuario dice que solo está mirando/comparando (spec 04). No es un dato del lead: no se persiste en `leads`, se escribe en el estado de sesión (dialog state). Puede ir solo, sin ningún otro campo |

Todos los campos son opcionales (upsert parcial: solo se actualiza lo que llega). Al menos un campo debe estar presente, si no → `error.code=EMPTY_UPDATE` — `solo_mirando=true` por sí solo cuenta como presente, no dispara ese error.

**Comportamiento:** persiste vía `LeadService.upsert(user_id, ...)`; la **etapa se recalcula en el dominio** (máquina de estados, spec 04) a partir del lead resultante — el LLM nunca la asigna directamente. Devuelve `{status: "ok", data: {lead: {...}, etapa: str}}` y el backend emite SSE `lead.updated`.

## 3. `solicitar_contacto_humano`

**Input**
| Campo | Tipo | Regla |
|---|---|---|
| `motivo` | `enum` | `TEST_DRIVE \| COTIZACION_FORMAL \| COMPRA_INMEDIATA \| DISCONFORMIDAD \| FUERA_DE_ALCANCE` |
| `resumen_requerimiento` | `str` | 10–500 caracteres |
| `canal_preferido` | `enum?` | mismo enum que `guardar_lead` |
| `urgencia` | `enum?` | `BAJA \| MEDIA \| ALTA` |

**Comportamiento:**
1. Requiere confirmación del usuario antes de ejecutarse — vía confirmación nativa de tools de ADK (`tool_context.request_confirmation`). El spike de F3 confirmó que funciona sobre nuestro SSE, así que **no se implementa fallback**: ver ADR-002.
2. **Idempotente por sesión:** máximo un handoff `OPEN` por `session_id`, garantizado por un índice único parcial en Postgres (`WHERE status = 'OPEN'`) además de la comprobación del servicio. Si ya existe uno abierto, la tool no crea otro: devuelve el existente con `ya_existia: true` y el agente lo comunica ("ya tienes una solicitud en curso").
3. Al confirmarse, crea el handoff en estado `OPEN` (transiciones `OPEN → IN_PROGRESS → CLOSED` gestionadas por `PATCH /api/v1/handoffs/{id}`, spec 02) y la etapa del diálogo pasa a `DERIVADO` (spec 04).
   Al cancelarse, no crea nada y la etapa vuelve a `stage_previa`.
4. Devuelve `{status: "ok", data: {handoff_id, ticket, motivo, status: "OPEN", ya_existia}}`. El `ticket` es `TICK-` más el id de la tabla con padding: persistente y auditable, a diferencia del `Math.random` del baseline (brecha #3).

## 4. `search_knowledge_base`

Equivalente al nodo `base_conocimientos_autos` del baseline, ahora con umbral y fuente explícitos.

**Input**
| Campo | Tipo | Regla |
|---|---|---|
| `query` | `str` | 1–300 caracteres |
| `categoria` | `enum?` | `CARROCERIAS \| SEGMENTOS \| MOTORIZACION \| TRANSMISION \| CONSUMO \| MANTENIMIENTO \| SEGURIDAD \| USO \| GLOSARIO` |
| `top_k` | `int` | 1–8, default 4 |

**Comportamiento:** embebe `query` con el `Embeddings` configurado, busca por coseno en `kb_chunks` (filtrando por `categoria` si viene), ordena por score. Si el mejor score < `RAG_MIN_SCORE` (env) → `status: "no_results"`, `data: null` — el agente usa la frase honesta del baseline (spec 05, 07). Si hay resultados: `data: {"resultados": [{"chunk_id", "title", "categoria", "source", "score", "content"}]}`, longitud `top_k`.

## 5. Guardrails de tools (L3, ver spec 07)

- Validación Pydantic estricta antes de tocar `application/` — cualquier campo fuera de enum o rango rechaza sin llegar a la DB.
- `session_id`/`user_id` siempre desde `ToolContext`, nunca del LLM.
- Máximo N llamadas a tools por turno (env `MAX_TOOL_CALLS_PER_TURN`, default 4) — evita loops; al superarse, la tool siguiente devuelve `status: "error"`, `error.code=TOOL_CALL_LIMIT`.
- PII (`telefono`, `email`) enmascarada en spans/logs de telemetría (spec 08), nunca en claro.
