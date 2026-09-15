# ADR-003 · Modelos locales con Ollama

## Estado
Aceptado — adelantado de F8 (P2) a F6 por decisión del humano el 2026-09-15.

## Contexto

`00-master-build.md` planeaba los modelos locales para F8, como P2. Se adelantaron porque el proyecto no tenía una `GOOGLE_API_KEY` con billing y eso bloqueaba tres cosas a la vez: verificar F4 en el navegador, ingerir la KB con embeddings reales, y calibrar `RAG_MIN_SCORE` contra una distribución real de scores.

Hardware disponible: RTX 5080 (16 GB de VRAM), 32 GB de RAM, Ollama 0.24 en Docker con acceso a GPU.

## Decisión

Perfil local por defecto, intercambiable a Gemini cambiando solo variables de entorno:

| Rol | Local | Gemini |
|---|---|---|
| Agente | `ollama_chat/gemma4:latest` (8B, Q4_K_M, 9.6 GB) | `gemini-3.8-flash` |
| Guardrail L2 / eval / fallback | `ollama_chat/qwen3:4b-instruct` | `gemini-3.5-flash-lite` / `-flash` / `gemini-3.7-flash` |
| Embeddings | `embeddinggemma` (768 dims) | `gemini-embedding-001` |

El puerto `EmbeddingsPort` y `build_base_model` aíslan la diferencia: fuera de `container.py` y `config.py`, ninguna capa sabe qué proveedor está activo.

## Hallazgos de la integración

Cada uno costó una iteración y ninguno estaba en la documentación.

### 1. Gemma 4 solo llama tools si el "thinking" está activo

Con `think: false` el modelo **ignora por completo** las tools: responde en prosa "voy a consultar mi base de conocimientos" y no emite ninguna `tool_call`. Con `think: true` las llama correctamente. Verificado contra la API de Ollama directamente, aislando ADK y LiteLLM.

Como el agente entero depende de las tools, `OLLAMA_THINK=true` no es opcional en el perfil local.

### 2. El razonamiento se filtraba a la pantalla

Con el thinking activo, ADK convierte el razonamiento en `types.Part(text=..., thought=True)`. Nuestro traductor de SSE concatenaba **todas** las partes, así que el usuario veía el monólogo interno del modelo ("Thinking Process: 1. Analyze the user input…") antes de la respuesta.

Solución: `agent/parts.py::visible_text()` omite las partes con `thought=True`, y se usa en los tres sitios que arman texto (SSE, historial de mensajes y el filtro L4). Aplica igual a Gemini, que marca el pensamiento de la misma forma.

### 3. LiteLLM resuelve el proveedor desde `llm_request.model`

`ResilientLlm` envuelve al modelo real para reintentos y respaldo (spec 07). LiteLLM no mira el campo `model` de su propia instancia sino `llm_request.model`, que ADK rellena con el nombre canónico del agente — es decir, el del envoltorio. Resultado: `BadRequestError: LLM Provider NOT provided. You passed model=resilient`.

Solución: `ResilientLlm._call` fija `llm_request.model` al del delegado antes de invocarlo, de modo que cada modelo (principal o respaldo) ve su propio identificador.

### 4. Turnos sin texto visible

Gemma 4 a veces produce solo razonamiento y ninguna respuesta, lo que dejaba una burbuja vacía en la UI. El traductor ahora detecta el turno sin texto visible y emite una frase de recuperación, salvo cuando el turno termina legítimamente sin texto (una confirmación HITL pendiente o un error ya reportado).

### 5. El contexto hay que declararlo

`gemma4` declara 131072 tokens de contexto, pero Ollama usa su default (mucho menor) y **recorta en silencio** si no se le indica otra cosa. Se pasa `num_ctx` explícito en cada llamada, desde `OLLAMA_CONTEXT_LENGTH` (16384 con 16 GB de VRAM; 32768 con 24 GB o más).

### 6. El prefijo importa y se valida

`ollama/` puede provocar loops de tool-calling; solo `ollama_chat/` se trata como modelo conversacional. `Settings` rechaza el arranque si `LLM_PROVIDER=ollama` y `AGENT_MODEL` no empieza con `ollama_chat/`, con un mensaje que explica cuál usar.

### 7. `LiteLlm` no viene en la instalación base

`from google.adk.models.lite_llm import LiteLlm` falla con `ImportError` en `google-adk` pelado. Hace falta el extra: `google-adk[extensions]==2.9.1`.

## Rendimiento medido (RTX 5080, gemma4 8B Q4_K_M)

| Turno | Latencia |
|---|---|
| Primera llamada tras arrancar (carga del modelo en VRAM) | 20–40 s |
| Turno conversacional sin tools | 1,4–2,2 s |
| Turno con una tool + RAG | 12–18 s |

La carga inicial es de Ollama, no del backend: el modelo se queda residente y a partir del segundo turno la latencia es cómoda para un chat.

## Diferencias frente a Gemini

- **Calidad conversacional:** Gemma 4 respeta el rol, el tuteo peruano, el límite de 2–3 oraciones y las frases canned. La respuesta de RAG queda bien fundamentada en los fragmentos recuperados.
- **Consistencia de tools:** menor que la de Gemini. En una corrida capturó `nombre` y `uso_principal`; en otra solo `nombre`. La máquina de estados no se rompe porque la etapa la recalcula el dominio, no el modelo.
- **Latencia:** un turno con tools tarda unos 15 s contra los ~2–3 s típicos de Gemini Flash.
- **Costo y privacidad:** cero costo por token y ningún dato sale del equipo, que es lo que lo hace viable para desarrollar y demostrar sin cuenta de facturación.

## Consecuencias

- El repo arranca sin ninguna API key: `docker compose up` más los dos `ollama pull` y el proyecto funciona completo.
- `docker-compose.local-llm.yml` levanta su propio Ollama con volumen y job de descarga; `docker-compose.gpu.yml` añade la GPU aparte, para no romper el arranque en equipos sin NVIDIA. Quien ya tenga Ollama corriendo puede apuntar `OLLAMA_API_BASE` al suyo y omitir ambos.
- `RAG_MIN_SCORE` quedó calibrado para `embeddinggemma` (0.42). Cambiar de modelo de embeddings obliga a re-ingerir **y** a re-calibrar; el chequeo de arranque detecta lo primero, lo segundo es manual.
- Volver a Gemini es cambiar seis variables de entorno y re-ingerir la KB. No hay código condicionado al proveedor fuera de `container.py` y `config.py`.
