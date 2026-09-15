# 11 · Proveedores de LLM y embeddings

## 1. Puerto `LlmProvider`

`domain/ports.py` define el `Protocol`; dos adaptadores en `infrastructure/llm/`:

| Adaptador | Uso | Selección |
|---|---|---|
| Gemini | Default | AI Studio o Vertex AI, según `GOOGLE_GENAI_USE_VERTEXAI` |
| Ollama / Gemma 4 | Local (P2, spec 13) | Vía LiteLLM, `LLM_PROVIDER=ollama` |

Ningún modelo se hardcodea: `AGENT_MODEL`, `GUARDRAIL_MODEL`, `EVAL_MODEL`, `FALLBACK_MODEL` son variables de entorno obligatorias (falla al arrancar si faltan y el provider correspondiente está activo). Los IDs de modelo Gemini cambian con frecuencia — se verifican contra la documentación oficial vigente antes de fijarlos en `.env.example`, nunca se asumen de memoria (gotcha #6, prompt maestro).

## 2. Gemini

- Dos backends posibles bajo el mismo adaptador: AI Studio (`GOOGLE_API_KEY`) o Vertex AI (`GOOGLE_GENAI_USE_VERTEXAI=true` + credenciales de proyecto GCP). El `Settings` valida que las variables necesarias para el backend elegido estén presentes.
- Sin `temperature` fija para `AGENT_MODEL` (spec 05 §3): Gemini 3.x recomienda el default; valores bajos pueden inducir loops de tool-calling.
- `gemini-embedding-2` no acepta `task_type` como parámetro de la API: la instrucción de tarea (p. ej. "retrieval query" vs. "retrieval document") va como texto dentro del prompt de embedding, no como argumento estructurado.
- El free tier responde 429 con relativa frecuencia bajo uso de demo/pruebas → backoff exponencial + `FALLBACK_MODEL` (spec 07 §3) no es opcional, es parte del camino feliz esperado en desarrollo.

## 3. Ollama / Gemma 4 (P2, detalle en spec 13)

- Prefijo obligatorio `ollama_chat/` en LiteLLM (no `ollama/`): el prefijo `ollama/` puede producir loops de tool-calling e ignorar contexto en algunos modelos.
- `OLLAMA_API_BASE` por env, sin default de host embebido en código (para soportar contenedor, host nativo o GPU).

## 4. Puerto `Embeddings`

| Adaptador | Modelo | Dimensión |
|---|---|---|
| Gemini | `gemini-embedding-001` o `gemini-embedding-2` | proyectado/truncado a 768 |
| Ollama | `embeddinggemma` | 768 nativas |

768 se eligió porque pgvector indexa (HNSW/IVFFlat) hasta 2000 dimensiones en el tipo `vector`, y 768 es compatible con ambos proveedores sin necesitar dos esquemas de tabla. Cambiar de proveedor de embeddings implica re-ingesta completa (spec 06 §4): el chequeo de arranque lo fuerza si detecta un `embedding_model` distinto en `kb_chunks`.

## 5. Variables de entorno (resumen)

`LLM_PROVIDER` (`gemini`|`ollama`), `GOOGLE_API_KEY`, `GOOGLE_GENAI_USE_VERTEXAI`, `AGENT_MODEL`, `GUARDRAIL_MODEL`, `EVAL_MODEL`, `FALLBACK_MODEL`, `OLLAMA_API_BASE`, `EMBEDDINGS_PROVIDER`, `EMBEDDINGS_MODEL`. Documentadas y comentadas en `.env.example` (F1).
