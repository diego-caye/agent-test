# Notas · API de ADK 2.x verificada

Verificado por introspección del paquete instalado el 2026-09-15. **Versión: `google-adk==2.9.1`** (pineada exacta en `backend/pyproject.toml`). No escribir ADK de memoria: si se sube de versión, re-verificar esta tabla.

## 1. Agente

```python
from google.adk.agents import Agent  # Agent is LlmAgent
```

| Campo | Tipo verificado |
|---|---|
| `instruction` | `str \| Callable[[ReadonlyContext], str \| Awaitable[str]]` |
| `global_instruction` | igual que `instruction` |
| `model` | `str \| BaseLlm` |
| `tools` | `list[Callable \| BaseTool \| BaseToolset]` |
| `generate_content_config` | `genai_types.GenerateContentConfig \| None` |

**Decisión:** usamos `instruction` **como callable**, no como string con `{state_key}`. Razón: la ficha del lead se inyecta como JSON y las llaves `{}` del JSON colisionan con el templating de placeholders de ADK. El callable recibe `ReadonlyContext` y arma el texto (spec 05 §1).

`ReadonlyContext` expone: `state`, `user_id`, `session`, `invocation_id`, `agent_name`, `user_content`, `run_config`.

## 2. Runner y streaming

```python
Runner(*, app=None, app_name=None, agent=None, plugins=None, session_service, ...)
Runner.run_async(*, user_id, session_id, invocation_id=None, new_message=None,
                 state_delta=None, run_config=None, yield_user_message=False)
    -> AsyncGenerator[Event, None]
```

- Todos los parámetros son **keyword-only**.
- `state_delta` permite inyectar estado en el turno sin escribir en la sesión antes — útil para pasar la etapa recalculada.
- Usamos siempre `run_async`, nunca `run` (gotcha: con `run` el contexto de OTel no llega a los spans hijos).
- **Streaming parcial:** `RunConfig(streaming_mode=StreamingMode.SSE)`. `StreamingMode` verificado: `NONE`, `SSE`, `BIDI`.
- `RunConfig.max_llm_calls` existe y acota las llamadas al modelo por invocación (relacionado con `MAX_TOOL_CALLS_PER_TURN`, spec 07 L3).

Construimos el Runner con `app=App(...)` (no con `agent=`), porque `App` es lo que acepta `plugins` y `events_compaction_config`.

## 3. Eventos

```python
from google.adk.events import Event
```

| Campo/método | Uso en nuestro SSE (spec 02) |
|---|---|
| `event.partial: bool \| None` | `True` en los deltas de texto → `message.delta` |
| `event.content: genai_types.Content \| None` | texto en `content.parts[*].text` |
| `event.get_function_calls()` | → `tool.started` |
| `event.get_function_responses()` | → `tool.finished` |
| `event.usage_metadata` | tokens in/out del turno → `message.completed` |
| `event.is_final_response()` | cierre del turno |
| `event.turn_complete`, `event.finish_reason` | fin de turno / motivo |
| `event.error_code`, `event.error_message` | → SSE `error` |
| `event.actions: EventActions` | ver abajo |
| `event.invocation_id`, `event.author`, `event.id`, `event.timestamp` | correlación y trazas |

`EventActions` (campos relevantes): `state_delta`, `escalate`, `skip_summarization`, `transfer_to_agent`, `requested_tool_confirmations`, `compaction`.

## 4. Sesiones y estado

```python
from google.adk.sessions import DatabaseSessionService

DatabaseSessionService(db_url: str | None = None, db_engine: AsyncEngine | None = None, **kwargs)
```

Métodos verificados: `create_session(*, app_name, user_id, state=None, session_id=None) -> Session`, `get_session(*, app_name, user_id, session_id, config=None) -> Session | None`, `list_sessions(*, app_name, user_id=None) -> ListSessionsResponse`, `append_event(session, event)`, `get_user_state(*, app_name, user_id) -> dict[str, Any]`, `prepare_tables()`, `delete_session`, `close`, `flush`.

- `db_url` debe ser `postgresql+asyncpg://...` (spec 06 §1).
- `prepare_tables()` crea el esquema de sesiones de ADK: se llama en el lifespan de la app.
- **`get_user_state`** es la forma soportada de leer el estado de alcance usuario sin abrir una sesión: es lo que permite saludar por nombre en una sesión nueva (AT-02).

### Prefijos de scope de estado (resuelve la duda abierta de spec 06 §1)

| Prefijo | Alcance |
|---|---|
| *(sin prefijo)* | solo esa sesión |
| `user:` | **persistente entre sesiones del mismo `user_id`** |
| `app:` | todos los usuarios |
| `temp:` | solo la invocación actual |

La etapa y las banderas van sin prefijo (por sesión). El lead **no** se replica bajo `user:`: la tabla `leads` es la única fuente de verdad y el proveedor de instrucción la consulta en cada turno (spec 06 §1). `user:` queda disponible por si alguna bandera futura necesita alcance de usuario.

## 5. Compactación de memoria (resuelve la duda abierta de spec 06 §2)

```python
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig

App(
    name=...,
    root_agent=...,
    plugins=[...],
    events_compaction_config=EventsCompactionConfig(
        token_threshold=...,        # MEMORY_COMPACTION_TOKEN_THRESHOLD
        event_retention_size=...,   # MEMORY_COMPACTION_KEEP_RECENT
        summarizer=None,            # opcional: LlmEventSummarizer(llm=Gemini(model=...))
    ),
)
```

Campos verificados de `EventsCompactionConfig`: `summarizer`, `compaction_interval`, `overlap_size`, `token_threshold`, `event_retention_size`.

## 6. Tools y HITL

```python
from google.adk.tools import ToolContext
```

`ToolContext` expone (verificado): `state`, `user_id`, `session`, `invocation_id`, `actions`, `function_call_id`, `agent_name`, **`request_confirmation`**, **`tool_confirmation`**, `search_memory`, `save_artifact`, …

- **`tool_context.user_id`** y **`tool_context.session.id`** son la fuente de `user_id`/`session_id` en las tools: nunca parámetros del LLM (spec 03, brecha #4 del baseline).
- Reglas de function tools: docstring claro (se manda al LLM), type hints obligatorios, **sin valores por defecto**, devolver `dict` serializable, no mencionar `tool_context` en el docstring.
- **HITL (F3):** `tool_context.request_confirmation(...)` + `EventActions.requested_tool_confirmations` es el camino primario. Sigue marcado como experimental → el spike de F3 decide, y ADR-002 documenta el resultado.

## 7. Modelos

```python
from google.adk.models import Gemini   # campos: model, client, client_kwargs, base_url, api_version, ...
```

- Gemini se puede pasar como `str` (el ID del modelo) directamente en `Agent(model=...)`; usamos el string de env (`AGENT_MODEL`).
- AI Studio: `GOOGLE_API_KEY` (también acepta `GEMINI_API_KEY`). Vertex: `GOOGLE_GENAI_USE_VERTEXAI=True` + `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION`.
- **`LiteLlm` no viene en la instalación base:** `from google.adk.models.lite_llm import LiteLlm` falla con `ImportError: LiteLLM support requires: pip install google-adk[extensions]`. F8 (Ollama, P2) tendrá que agregar el extra `google-adk[extensions]` a `pyproject.toml`.

## 8. Plugins (F6)

```python
from google.adk.plugins.base_plugin import BasePlugin
App(name=..., root_agent=..., plugins=[MyPlugin()])
```

Los plugins corren **antes** que los callbacks de agente y aplican a todos los sub-agentes. Hooks por keyword (los nombres de parámetro deben coincidir exactamente), p. ej. `async def before_model_callback(self, *, callback_context, llm_request)`. Devolver `None` observa; devolver un valor interviene. Es la capa donde viven L1/L2/L4 (spec 07).
