# 01 · Arquitectura

## 1. Vista de componentes

```
┌────────────┐   HTTPS/SSE   ┌─────────────────────────────┐
│  Frontend  │──────────────▶│  FastAPI (api/)              │
│ React+Vite │◀──────────────│   → application/              │
└────────────┘   JSON/SSE    │      → domain/ (puro)         │
                              │      ← infrastructure/        │
                              │   agent/ (ADK Agent + tools)  │
                              └───────┬──────────┬────────────┘
                                      │          │
                         ┌────────────▼──┐   ┌───▼─────────────┐
                         │ PostgreSQL     │   │ LLM provider     │
                         │ + pgvector     │   │ Gemini | Ollama  │
                         │ (sesiones ADK, │   │ (LiteLLM)        │
                         │ leads, kb_chunks,│  └──────────────────┘
                         │ handoffs, ...) │
                         └────────────────┘
                                      │
                              ┌───────▼────────┐
                              │ OTel → Langfuse │
                              └─────────────────┘
```

## 2. Capas del backend

`backend/src/asesor/{api,application,domain,agent,infrastructure}` (estructura completa en `00-master-build.md` §3).

- **Regla de dependencia:** `api → application → domain ← infrastructure`. `domain` no importa ADK, FastAPI ni SQLAlchemy — son `Protocol`s y entidades puras, testeables sin red ni DB.
- **`agent/`** depende de `application` (llama a los mismos servicios que usa `api/`), nunca al revés: las tools son adaptadores delgados que traducen argumentos del LLM a llamadas de servicio y el resultado a un envelope (spec 03).
- **`application/`** orquesta casos de uso (`ChatService`, `LeadService`, `HandoffService`, `KnowledgeService`, `TitleService`, `EvaluationService`) contra los puertos definidos en `domain/` o, para los repositorios más simples, directamente contra su implementación SQL concreta.
- **`infrastructure/`** implementa esos puertos: repositorios SQLAlchemy, retriever pgvector, adaptadores de embeddings y LLM, telemetría, fault injection.

## 3. Puertos clave

El `Protocol` no está centralizado en `domain/ports.py` para todo: vive ahí para `LeadRepository` (el primero, F2) y junto al servicio que lo usa para `HandoffRepository` (`application/handoff_service.py`) — desacoplar pagó su costo en ambos porque los tests los reemplazan por dobles en memoria desde el día uno. Los repositorios que se sumaron después (`session_titles`, `feedback`, `evaluations`) se inyectan por su clase SQL concreta directamente, sin `Protocol` intermedio: solo hay una implementación real y añadir la interfaz no cambiaría cómo se testean (ya usan una clase "fake" con el mismo contrato duck-typed, spec 09).

| Puerto | Dónde vive el `Protocol` | Implementaciones | Usado por |
|---|---|---|---|
| `LlmProvider` | (firma de ADK, no propio) | Gemini (AI Studio/Vertex), Ollama vía LiteLLM | `agent/` factory del `Agent`, `TitleService`, `EvaluationService`, resumidor de compactación (spec 06 §2) |
| `EmbeddingsPort` | `domain/knowledge.py` | Gemini (`gemini-embedding-001`/`-2`), Ollama (`embeddinggemma`) | `KnowledgeService`, `scripts/ingest_kb.py` |
| `LeadRepository` | `domain/ports.py` | `SqlLeadRepository` | `LeadService` |
| `HandoffRepository` | `application/handoff_service.py` | `SqlHandoffRepository` | `HandoffService` |
| `SqlSessionTitleRepository`, `SqlFeedbackRepository`, `SqlEvaluationRepository` | sin `Protocol`, clase concreta | (ellas mismas) | `TitleService`, router de feedback, `EvaluationService` |
| `KnowledgeRetriever` | `domain/knowledge.py` | pgvector HNSW coseno (`PgVectorRetriever`) | `KnowledgeService` |

`Settings` (`config.py`) valida combinaciones inválidas de provider al arrancar (p. ej. `EMBEDDINGS_PROVIDER=ollama` con `LLM_PROVIDER` en modo que no lo soporte) y falla rápido con un mensaje claro.

## 4. Flujo de un turno de chat

1. Frontend hace `POST /api/v1/chat/stream {session_id, message}` con header `X-User-Id`.
2. `api/` valida que la sesión pertenezca al usuario (404 si no), abre un `trace_id`, delega a `ChatService`.
3. `ChatService` invoca `runner.run_async(...)` sobre el `Agent` "Luis"; los plugins L1/L2 corren antes del modelo (spec 07).
4. El `Agent` decide si llama tools (`guardar_lead`, `solicitar_contacto_humano`, `search_knowledge_base`); cada tool pasa por L3 y golpea `application/`.
5. Eventos ADK se mapean a SSE (`message.delta`, `tool.started/finished`, `lead.updated`, `hitl.confirmation_required`, `guardrail.triggered`, `error`) — contrato completo en spec 02.
6. Al cerrar el turno: L4 revisa la salida, se registran latencia/tokens (spec 08), se persiste el evento en la sesión ADK.

## 5. Por qué ADK (resumen; detalle en ADR-001)

`google-adk` da `Runner`, `DatabaseSessionService`, compactación de eventos y confirmación de tools nativa — resuelve memoria y HITL sin reinventar infraestructura, y separa el núcleo decisional de la UI (requisito del reto). LangGraph se descartó por mayor esfuerzo de integración con Postgres/HITL para el alcance y plazo del reto; mantener n8n se descartó por no cumplir "desacoplado de la UI" ni permitir tests/observabilidad de grado producción.

## 6. Trade-offs y qué revisar si escala

| Decisión | Trade-off aceptado | Revisar si escala |
|---|---|---|
| Un solo `Agent` con 3 tools | Simplicidad, un único prompt que mantener | Si crecen las tools/dominios, considerar sub-agentes ADK especializados con enrutamiento |
| SSE propio sobre `run_async` en vez de `adk api_server` | Control total del contrato HTTP y de guardrails, pero mantenimiento propio del streaming | Reevaluar `api_server` si ADK lo estabiliza y cubre confirmación de tools + auth propia |
| Postgres único (sesiones + pgvector + tablas propias) | Un solo servicio que operar, transacciones simples | Separar OLTP de vectorial (o usar un vector store dedicado) si el volumen de KB o QPS de RAG crece mucho |
| `DatabaseSessionService` de ADK para memoria | Reutiliza compactación y scoping oficial | Si el volumen de eventos por sesión es muy alto, revisar políticas de retención/purga explícitas |
| Confirmación de tools de ADK (experimental) para HITL | Menos código propio si funciona | Fallback ya diseñado (ADR-002); si ADK no lo estabiliza, el fallback pasa a ser el camino principal |
| Observabilidad vía Langfuse sin keys = no-op | La app nunca depende de un servicio externo para arrancar | Si se requiere alerting, agregar un exporter adicional (p. ej. Prometheus) sin tocar el dominio |

## 7. Infraestructura

Un único `docker-compose.yml` (db, backend, frontend; Ollama bajo el perfil opcional `local-llm`, que asume GPU NVIDIA). `backend` y `frontend` montan el código fuente y recargan en caliente, así que `--build` solo hace falta cuando cambian las dependencias. `Makefile` con targets `up`, `up-llm`, `rebuild`, `down`, `lint`, `typecheck`, `test`, `ingest-kb`, `migrate`. Ver spec 11 para el perfil de modelos locales.
