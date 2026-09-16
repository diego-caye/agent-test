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
| Agente | `ollama_chat/qwen3:4b` con `OLLAMA_THINK=low` | `gemini-3.8-flash` |
| Guardrail L2 / eval | `ollama_chat/qwen3:4b-instruct` | `gemini-3.5-flash-lite` / `-flash` |
| Fallback | `ollama_chat/llama3.2:latest` | `gemini-3.7-flash` |
| Embeddings | `embeddinggemma` (768 dims) | `gemini-embedding-001` |

El agente pasó por tres candidatos antes de quedar fijo, y cada cambio salió de una medición:

1. `gemma4:latest` — no entra en la VRAM libre, se parte a CPU (§ "Elegir el modelo por VRAM libre").
2. `qwen3:4b-instruct` — rapidísimo (1,2 s) y 100% en GPU, pero **nunca llamaba `guardar_lead`**. Llamaba las otras dos tools, así que no era un problema de cableado: la variante sin razonamiento no decide bien una tool de guardado silencioso.
3. `qwen3:4b` (con thinking) — llama las tres tools de forma consistente. Es el que queda.

Gemma 4 sigue documentado como la opción de más calidad para equipos con más VRAM libre.

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

## Elegir el modelo por VRAM libre, no por VRAM instalada

Este fue el hallazgo con más impacto práctico. La RTX 5080 tiene 16,3 GB, pero con el escritorio de Windows y el resto de contenedores corriendo, **quedaban ~9,0 GB libres**. `gemma4:latest` ocupa ~10 GB, así que no entraba: Ollama repartió las capas y dejó dos tercios del modelo en CPU.

El síntoma engaña, porque el modelo *funciona*: responde bien, llama tools, respeta el rol. Solo es lento. `ollama ps` es lo que lo delata, en la columna `PROCESSOR`.

Medido en la RTX 5080, turno caliente (modelo ya cargado):

| Modelo | `num_ctx` | Latencia | Reparto |
|---|---|---|---|
| `qwen3:4b-instruct` | 32768 | **1,2 s** | **100% GPU** |
| `gemma4:latest` | 8192 | 16,4 s | 67% CPU / 33% GPU |
| `gemma4:latest` | 16384 | 19,3 s | 66% CPU / 34% GPU |
| `gemma4:latest` | 32768 | 32,4 s | 64% CPU / 36% GPU |

Dos conclusiones:

1. **Un modelo que no entra en VRAM cuesta un orden de magnitud.** No es un ajuste fino: son 1,2 s contra 19 s por turno.
2. **Ampliar el contexto solo es gratis si el modelo entra.** Subir `num_ctx` agranda el KV cache; con `gemma4` ya desbordado, pasar de 8k a 32k casi duplicó la latencia. Con `qwen3` a 32768 el modelo sigue entero en GPU y no cuesta nada.

Por eso el agente es `qwen3:4b-instruct` con 32768 de contexto: entra completo, deja margen para la instrucción (~2,2k tokens), los fragmentos de RAG y el historial.

### El razonamiento es el precio de que las tools funcionen

`qwen3:4b-instruct` respondía en 0,4–3,7 s pero no llamaba `guardar_lead`, así que la ficha del lead nunca se llenaba — y capturar el lead es un requisito del reto, no un adorno. La variante con razonamiento sí la llama, y se paga en latencia:

| Configuración | `guardar_lead` | Latencia por turno |
|---|---|---|
| `qwen3:4b-instruct` (sin thinking) | **no** | 0,4–3,7 s |
| `qwen3:4b` + `think=low` | sí | 12–30 s |
| `qwen3:4b` + `think=true` | sí | 10–17 s |

Aislado, `think=low` responde en ~3 s. Dentro de la aplicación sube a 12–30 s porque el contexto real (instrucción de ~2,2k tokens más tres esquemas de tools) hace que el modelo razone mucho más, y ADK llama al modelo dos veces por turno cuando hay tool: una para decidirla y otra para redactar con el resultado.

Los niveles de razonamiento (`low`, `medium`, `high`) funcionan y resuelven la duda que spec 05 §3 dejaba abierta sobre si el SDK los expone: sí, vía el parámetro `think` de Ollama.

**Camino de mejora si la latencia molesta:** acortar la instrucción del sistema, que es lo que más infla el razonamiento. No se hizo aquí porque la instrucción codifica las frases canned y las reglas del baseline, y recortarla a ciegas arriesga fidelidad con el spec.

### Tabla orientativa por VRAM libre

| VRAM libre | Modelo sugerido | Contexto |
|---|---|---|
| ~4 GB | `qwen3:4b-instruct` o `llama3.2` | 8192–16384 |
| ~9 GB | `qwen3:4b-instruct` | 32768 |
| ~14 GB | `gemma4:latest` | 16384 |
| 24 GB o más | `gemma4` de mayor tamaño | 32768 |

Antes de fijar el modelo conviene medir lo que de verdad hay libre, con el modelo descargado:

```bash
docker exec <ollama> ollama stop <modelo>
docker exec <ollama> nvidia-smi --query-gpu=memory.free --format=csv
```

### 8. Los modelos pequeños escriben la llamada en vez de emitirla

Gemma 4 a veces devolvió la llamada a la tool **como texto** en la respuesta:

```
Hola 👋 Soy Luis, tu asesor automotriz. ¿Con quién tengo el gusto?
guardar_lead(nombre="Diego", uso_principal=None, tipo_vehiculo_interes=None, ...)
```

La tool nunca se ejecutaba y el usuario veía eso en la burbuja del chat. Se detectó mirando una captura del navegador, no en los tests: con el `FakeAdkLlm` no ocurre.

L4 ahora detecta y elimina esas pseudo-llamadas (`strip_pseudo_tool_calls`). No arregla que la tool no se ejecutara —eso depende del modelo— pero evita que el usuario vea código.

## Diferencias frente a Gemini

- **Calidad conversacional:** buena en ambos modelos locales. Respetan el rol, el tuteo peruano, el límite de 2–3 oraciones y las frases canned del baseline. La respuesta de RAG queda fundamentada en los fragmentos recuperados.
- **Consistencia de tools:** menor que la de Gemini. En una corrida el agente capturó `nombre` y `uso_principal`; en otra solo `nombre`; en otra escribió la llamada como texto. La máquina de estados no se rompe porque la etapa la recalcula el dominio, no el modelo.
- **Latencia:** con el modelo bien dimensionado, comparable a Gemini Flash (~1–2 s por turno conversacional).
- **Costo y privacidad:** cero costo por token y ningún dato sale del equipo. Es lo que hace viable desarrollar y grabar la demo sin cuenta de facturación.

## Consecuencias

- El repo arranca sin ninguna API key: `docker compose up` más los dos `ollama pull` y el proyecto funciona completo.
- `docker-compose.local-llm.yml` levanta su propio Ollama con volumen y job de descarga; `docker-compose.gpu.yml` añade la GPU aparte, para no romper el arranque en equipos sin NVIDIA. Quien ya tenga Ollama corriendo puede apuntar `OLLAMA_API_BASE` al suyo y omitir ambos.
- `RAG_MIN_SCORE` quedó calibrado para `embeddinggemma` (0.42). Cambiar de modelo de embeddings obliga a re-ingerir **y** a re-calibrar; el chequeo de arranque detecta lo primero, lo segundo es manual.
- Volver a Gemini es cambiar seis variables de entorno y re-ingerir la KB. No hay código condicionado al proveedor fuera de `container.py` y `config.py`.
