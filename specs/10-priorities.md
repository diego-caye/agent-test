# 10 · Prioridades

Plazo: viernes 18-sep-2026, 15:00 (hora Perú). Si falta tiempo: recortar P2 primero, luego P1; **nunca P0**.

## P0 — imprescindible para el reto

- Backend con arquitectura por capas, Settings validado, CI en verde (F1)
- Agente "Luis" en ADK con `guardar_lead`, máquina de estados, sesiones Postgres, SSE, telemetría base (F2)
- `solicitar_contacto_humano` con HITL (confirmación o fallback), handoffs, endpoints admin (F3)
- Frontend de chat en tiempo real conectado por API, flujo end-to-end (F4)
- RAG (`search_knowledge_base`) con KB ingerida y AT de RAG/sin datos (F5)
- Guardrails L1 y L3, fallbacks de tool/modelo/RAG/DB, fault injection para la demo (F6, L2/L4 son P1 dentro de esta fase)
- README, diagramas, video de 5–7 min, specs sincronizados, PR `develop → main`, tag `v1.0.0` (F9)

## P1 — valioso, no bloquea la entrega mínima

- Guardrails L2 (clasificador) y L4 (salida) — sin ellos, L1+L3 ya cubren los AT de inyección directa del reto
- Feedback de usuario (`POST /feedback`) y evaluación post-ejecución (F7)
- Compactación de memoria explícita vía `EventsCompactionConfig` con umbrales afinados (sin ella, ADK igual mantiene memoria, solo sin control fino de tokens)
- Evalset ADK ejecutable

## P2 — nice-to-have si sobra tiempo

- Modelos locales (Ollama/Gemma 4) y sus overrides de Docker (F8, ADR-003)
- Vista de operador de handoffs en la UI (más allá de los endpoints admin crudos)
- Panel dev completo (fault injection ya es P0 mínimo funcional; refinamientos visuales son P2)
- Ruta a producción en GCP (Cloud Run + Cloud SQL) — solo se documenta en README, no se implementa

## Relación con la rúbrica

| Área rúbrica | Peso | Fases que la cubren |
|---|---|---|
| SDD y prompting | 20% | F0, spec 05 |
| Arquitectura agente + UI | 25% | F1, F2, F4 |
| Harness (tools, HITL, guardrails, fallbacks) | 20% | F2, F3, F6 |
| Memoria + RAG | 15% | F2, F5, F6 (spec 06) |
| UX | 10% | F4 |
| Observabilidad | 10% | F2 (base), F7 (feedback/evals) |

Priorizar P0 cubre el 100% de la rúbrica en su forma mínima; P1 refuerza harness y observabilidad; P2 es diferenciador pero no penaliza su ausencia si el tiempo aprieta.
