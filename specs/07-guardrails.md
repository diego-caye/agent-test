# 07 · Guardrails y fallbacks

## 1. Capas

| Capa | Dónde | Qué hace | Falla como |
|---|---|---|---|
| **L1 determinista** | Plugin ADK, antes del modelo | Longitud máxima del mensaje, normalización Unicode, caracteres invisibles/de control, patrones de inyección ES/EN (p. ej. "ignora tus instrucciones", "revela tu prompt", "a partir de ahora eres", etiquetas de rol tipo `system:`/`assistant:`, bloques base64/hex sospechosos) | Match → respuesta canned de jailbreak **sin llamar al LLM**; SSE `guardrail.triggered {layer: L1, category}` |
| **L2 clasificador** | **No implementado (P1)** — ver abajo | Diseño previsto: `GUARDRAIL_MODEL` con salida estructurada `{label: in_scope \| off_topic \| injection \| abuse, confidence}` | Timeout corto (`GUARDRAIL_L2_TIMEOUT_MS`) → **fail-open** (deja pasar) con log de warning — L4 sigue activo como red de seguridad de salida |
| **L3 tools** | Antes de ejecutar cada tool | Validación Pydantic, ids desde `ToolContext`, `MAX_TOOL_CALLS_PER_TURN`, PII enmascarada en spans (detalle en spec 03 §5) | Rechazo → envelope `status: error` que la tool devuelve al agente |
| **L4 salida** | Después del modelo, antes de enviar al usuario | Fuga del canary token → respuesta canned; menciones de precio/cotización/stock/descuento → mensaje seguro + oferta de derivación | Reemplaza el mensaje; SSE `guardrail.triggered {layer: L4, category}` |

L1 corre sobre el mensaje entrante del usuario (L2 correría ahí también, cuando exista); L3 sobre cada tool call; L4 sobre el mensaje saliente del modelo, antes de transmitirlo por SSE (se aplica al buffer completo, no a cada delta, para no filtrar antes de detectar la fuga).

**Estado real (verificado contra el código, F9):** solo están implementadas L1, L3 y L4 — coincide con `PROGRESS.md` F6 ("L2 clasificador (P1) — no implementado; L1 + L4 cubren los AT del reto"), no es una desviación nueva. `agent/guardrails/plugin.py` lo documenta en su propio docstring.

## 2. Categorías de `guardrail.triggered`

**Emitidas hoy** (verificado contra el código): `injection`/`too_long` desde L1 (`agent/guardrails/l1.py`), `pricing_leak`/`canary_leak`/`pseudo_tool_call` desde L4 (`agent/guardrails/l4.py`). `off_topic` y `abuse` son del diseño de L2 y no se emiten todavía — dependen de que se implemente el clasificador. Cada una mapea a una de las frases canned del baseline (jailbreak/off-topic) o a un mensaje L4 nuevo para `pricing_leak`/`canary_leak` (spec 05 §1, con oferta de derivación).

## 3. Fallbacks de infraestructura

| Falla | Camino |
|---|---|
| Excepción en una tool | Envelope `status: error`; el agente lo explica sin tecnicismos al usuario (nunca expone stack traces) |
| Modelo: 429 / 5xx / timeout | Backoff exponencial, 3 intentos (replica `retryOnFail`/`maxTries: 3` del baseline) → si se agotan, reintenta una vez con `FALLBACK_MODEL` → si también falla, mensaje amable + SSE `error {code, message, retryable: true}` |
| RAG caído (Postgres/pgvector no responde) | Mismo camino que `search_knowledge_base` → `no_results`: frase honesta del baseline, no se rompe el turno |
| DB caída (sesión/lead) | 503 con `{code: UPSTREAM_UNAVAILABLE, retryable: true}` y mensaje claro en la UI; `/readyz` ya lo reporta antes de que el usuario intente chatear |

## 4. Fault injection (demo)

Con `ENABLE_FAULT_INJECTION=true` (solo si `APP_ENV=dev`), el header `X-Debug-Fault: tool_error | model_429 | model_timeout | rag_down` en `POST /chat/stream` fuerza el fallo correspondiente **después** de pasar guardrails de entrada, para poder demostrar cada camino de fallback sin depender de que ocurra orgánicamente. Selector en el panel dev del frontend (spec `docs/ui.md`). Ignorado si `APP_ENV != dev`.

## 5. Variables de entorno

`GUARDRAIL_MODEL` (reservado para L2 cuando se implemente; mientras tanto, reutilizado como modelo liviano por `TitleService` y el resumidor de `EventsCompactionConfig` — spec 06 §2, spec 08 §5 — nada que ver con guardrails hoy), `GUARDRAIL_L2_TIMEOUT_MS`, `GUARDRAIL_CANARY_TOKEN`, `MAX_TOOL_CALLS_PER_TURN`, `FALLBACK_MODEL`, `ENABLE_FAULT_INJECTION`, `RAG_MIN_SCORE` (spec 06).

## 6. Principio de fail-safe

L1 y L3 son deterministas y **fail-closed** (si algo no se puede validar, se rechaza). L2 es probabilístico y **fail-open** (un LLM caído no debe tumbar el chat) — la razón por la que L4 existe como segunda red sobre la salida, no solo L2 sobre la entrada.
