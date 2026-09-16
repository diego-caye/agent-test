# 08 · Observabilidad y feedback

## 1. Pipeline

OpenTelemetry (SDK Python) + `openinference-instrumentation-google-adk` → exporter OTLP → Langfuse. Sin `LANGFUSE_*` configuradas, el exporter cae a no-op (`ConsoleSpanExporter` deshabilitado o `NoOpTracerProvider`) — la app funciona igual, solo sin backend de trazas. Nunca se lanza una excepción por telemetría ausente.

## 2. Spans propios

| Span | Atributos propios | Cuándo |
|---|---|---|
| `guardrail.l1` | `matched: bool`, `category?` | por cada mensaje entrante |
| `guardrail.l2` | `label`, `confidence`, `timed_out: bool` | por cada mensaje entrante (si L1 no bloqueó) |
| `guardrail.l4` | `matched: bool`, `category?` | por cada respuesta saliente |
| `rag.retrieve` | `query`, `categoria?`, `top_k`, `best_score`, `result_count` | cada `search_knowledge_base` |
| `hitl.request` | `motivo`, `session_id` | al proponer `solicitar_contacto_humano` |
| `hitl.confirm` | `approved: bool` | al resolver la confirmación |
| `eval.judge` | `criterio`, `score` | por cada criterio evaluado (spec §4) |

Todos son hijos del span de turno abierto por `ChatService` (que lleva `trace_id`).

## 3. Datos por turno

- `trace_id` se crea **antes** de invocar `runner.run_async` (nunca `run`: con `run` el contexto OTel no llega a los spans hijos — gotcha del prompt maestro).
- Latencia medida en servidor (desde que se recibe el POST hasta `message.completed`).
- Tokens in/out: suma de todas las llamadas LLM del turno (el agente **y** el clasificador L2 si corrió).
- Se emiten en el evento SSE `message.completed` (spec 02) y en un log JSON estructurado (`stdout`, un objeto por turno) para poder grepear sin depender de Langfuse.
- Atributos de span/log: `session_id`, `user_id`, `provider` (gemini/ollama), `model`, `etapa`, `guardrail_blocked: bool`, `hitl: bool`.
- PII (`telefono`, `email` del lead) se enmascara antes de entrar a cualquier span o log (spec 03 §5) — nunca en claro en Langfuse.

## 4. Feedback de usuario

`POST /api/v1/feedback {session_id, trace_id, score: 1 | -1, comment?}` → inserta en tabla `feedback` **y** registra un score `user-feedback` en Langfuse contra el `trace_id` recibido (Langfuse permite adjuntar scores a un trace ya cerrado). Si Langfuse no está configurado, solo se persiste en la tabla — no es bloqueante.

## 5. Evaluación post-ejecución (P1)

Tarea en background (no bloquea la respuesta al usuario) que corre con `EVAL_MODEL`, muestreada por `EVAL_SAMPLE_RATE` (env, 0–1), sobre una fracción de los turnos. Evalúa por turno:

| Criterio | Qué mide |
|---|---|
| Tono empático | Coherencia con la VOZ de "Luis" (spec 05) |
| Brevedad | 2–3 oraciones, sin markdown pesado |
| Una sola pregunta | No acumula varias preguntas en un turno |
| Sin precios | No menciona precios/cotizaciones/stock/financiamiento |
| Fidelidad al contexto RAG | Si hubo `search_knowledge_base` con resultados, la respuesta no contradice ni inventa sobre esos chunks |

Persiste en tabla `evaluations` (`session_id`, `message_id`, criterio, score, justificación corta) y emite scores `quality.<criterio>` en Langfuse contra el `trace_id` del turno. Nunca bloquea ni retrasa `message.completed`.

**Implementado en F7** (`EvaluationService`): una sola llamada al juez por turno (no una por criterio) que devuelve un veredicto JSON por criterio; `fidelidad_rag` solo se pide si el turno llamó `search_knowledge_base`. Se agenda como `BackgroundTasks` desde dentro de `_stream` (chat.py), una vez conocido el texto final del turno — no antes, porque a diferencia de `title_service` necesita el resultado, no solo el mensaje de entrada. Un turno reanudado por `chat/confirmations` (HITL) nunca se muestrea: no hay mensaje de usuario fresco que evaluar ahí.

Existe además el equivalente offline — un dataset dorado de conversaciones (`backend/tests/evalset/`, tipo `evalset` en spec 09) que corre contra el modelo real y el mismo mecanismo de juez, más trayectoria de tools y contención fuera de tema. Es la pieza de "correr conversaciones on-topic y off-topic para verificar que el agente no se sale de su guion" — offline y bajo demanda, no online por muestreo como este mecanismo.

## 6. Variables de entorno

`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `LANGFUSE_PROJECT_ID` (para el link del panel dev), `EVAL_MODEL`, `EVAL_SAMPLE_RATE`.

## 7. Qué mirar en Langfuse (para el README, F9)

Árbol de la traza de un turno (agente → tools → guardrails), latencia total vs. por span, tokens in/out acumulados, score `user-feedback` y scores `quality.*` cuando corrió la evaluación.
