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
| Agente | `ollama_chat/gemma4:latest` con `OLLAMA_THINK=low` | `gemini-3.8-flash` |
| Guardrail L2 / eval | `ollama_chat/qwen3:4b-instruct` | `gemini-3.5-flash-lite` / `-flash` |
| Fallback | `ollama_chat/llama3.2:latest` | `gemini-3.7-flash` |
| Embeddings | `embeddinggemma` (768 dims) | `gemini-embedding-001` |

El agente pasó por tres candidatos antes de quedar fijo, y cada cambio salió de una medición:

1. `gemma4:latest` — se repartía a CPU y tardaba 19 s por turno. Parecía no caber en VRAM; la causa real era otra (§ "El modelo local necesita RAM del sistema").
2. `qwen3:4b-instruct` — rapidísimo (1,2 s) y 100% en GPU, pero **nunca llamaba `guardar_lead`**. Llamaba las otras dos tools, así que no era un problema de cableado: la variante sin razonamiento no decide bien una tool de guardado silencioso.
3. `gemma4:latest` de nuevo, tras corregir el límite de RAM de WSL y liberar VRAM: **100% GPU, 5–10 s por turno y las tres tools funcionando**. Es el que queda.

`qwen3:4b` (con thinking) queda como alternativa: entra en GPU con mucha menos VRAM libre y también llama las tres tools, a cambio de respuestas más escuetas.

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

## El modelo local necesita RAM del sistema, no solo VRAM

Este fue el hallazgo con más impacto, y el diagnóstico inicial fue equivocado: parecía un problema de VRAM y en realidad eran **dos límites distintos apilados**.

En una RTX 5080 (16,3 GB) con 31 GB de RAM, `gemma4:latest` (~10 GB) corría dos tercios en CPU y tardaba 19 s por turno. Bajar el contexto no ayudaba. El error real solo apareció al pedirle a Ollama que cargara el modelo de cero:

```
model requires more system memory (6.7 GiB) than is available (6.0 GiB)
```

**Causa 1 — la VM de WSL.** Docker Desktop en Windows corre sobre WSL2, que sin `.wslconfig` toma por defecto el 50% de la RAM del equipo: 15,2 GB de los 31. Dentro de esa VM, con el resto de contenedores corriendo, a Ollama le quedaban ~6 GB de RAM del sistema, insuficientes para la parte del modelo que no entra en GPU. Los 31 GB del equipo no llegaban a Docker.

**Causa 2 — otros procesos reteniendo VRAM.** Otro contenedor del equipo (un servicio de síntesis de voz) mantenía su modelo cargado en GPU aunque estuviera ocioso, ocupando ~4,8 GB. No es un fallo: la mayoría de servicios de ML hacen *eager loading* porque cargar el modelo tarda, y además PyTorch no devuelve al driver la VRAM que libera, se la queda en su pool. Ollama es la excepción: descarga el modelo tras su `keep_alive`.

Con `.wslconfig` (`memory=24GB`) y ese contenedor detenido, quedaron 14,2 GB de VRAM libres y **`gemma4` pasó a 100% GPU con 32768 de contexto**.

| Configuración | Reparto | Latencia por turno |
|---|---|---|
| `gemma4`, WSL en 15 GB, otros modelos en GPU | 66% CPU / 34% GPU | 16–32 s |
| `gemma4`, WSL en 24 GB, VRAM liberada | **100% GPU** | **5–10 s** |
| `qwen3:4b-instruct` (comparación) | 100% GPU | 1,2 s |

### Cómo diagnosticarlo

`ollama ps` es lo que lo delata: la columna `PROCESSOR` dice si el modelo está entero en GPU o repartido.

```bash
docker exec <ollama> ollama ps                    # reparto CPU/GPU
docker exec <ollama> ollama stop <modelo>         # descargar
docker exec <ollama> nvidia-smi --query-gpu=memory.free --format=csv
wsl -d docker-desktop -e sh -c "free -h"          # RAM real de la VM
```

Si el modelo se reparte, revisar **las dos** cosas: VRAM libre y RAM disponible dentro de la VM de WSL.

### Sobre ampliar el contexto

Ampliar `num_ctx` agranda el KV cache. Con el modelo desbordado, subir de 8k a 32k casi duplicaba la latencia; con el modelo entero en GPU sale gratis.

Y ampliarlo es **necesario**, no opcional: los turnos reales de esta aplicación miden entre 2.400 y 9.600 tokens de entrada (instrucción de ~2,2k, tres esquemas de tools, fragmentos de RAG e historial). Con el default de Ollama el prompt se truncaría en silencio, que es lo que produce respuestas incoherentes o cortadas. De ahí `OLLAMA_CONTEXT_LENGTH=32768`.

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

### Tabla orientativa

Medir con el modelo descargado, porque lo que importa es lo que queda libre, no lo instalado.

| VRAM libre | RAM libre en la VM de WSL | Modelo sugerido | Contexto |
|---|---|---|---|
| ~4 GB | 4 GB | `llama3.2` | 8192 |
| ~9 GB | 8 GB | `qwen3:4b` | 32768 |
| ~14 GB | 16 GB | `gemma4:latest` | 32768 |
| 24 GB o más | 24 GB | `gemma4` de mayor tamaño | 32768 |

En Windows, además del modelo hay que dimensionar la VM de WSL en `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
memory=24GB
swap=8GB
autoMemoryReclaim=gradual
```

Los cambios requieren `wsl --shutdown`, que reinicia todos los contenedores. Los que tengan `restart: unless-stopped` vuelven solos.

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
