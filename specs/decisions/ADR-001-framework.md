# ADR-001 · Framework del núcleo decisional

## Estado
Aceptado

## Contexto

El reto pide migrar a código un workflow n8n de asesoría automotriz, con el núcleo decisional **desacoplado de la UI** (una UI web de chat lo consume por API), memoria multi-turn por sesión/usuario en SQL, tools con contrato explícito, HITL real, guardrails/fallbacks, y observabilidad de trazas/latencia/tokens. Ver brechas verificadas del baseline en `../00-baseline-analysis.md`.

Opciones evaluadas: **mantener n8n** (con mejoras), **Google ADK 2.x**, **LangGraph**.

## Opciones

### Mantener n8n
- Rápido de ajustar (ya existe el workflow).
- No cumple "desacoplado de la UI" de forma limpia: n8n es workflow-first, no una librería que se embeba en un backend propio con tests unitarios de dominio.
- Sin tipado, sin tests automatizables de la lógica de negocio, sin control fino de memoria/compactación, HITL nativo limitado, observabilidad de tokens/latencia manual.
- Descartada: no cumple los requisitos de arquitectura, harness y testing del reto.

### LangGraph
- Muy flexible para grafos de estados custom, buen ecosistema de observabilidad (LangSmith).
- Requiere construir a mano lo que ADK da out-of-the-box para este caso: persistencia de sesión en Postgres, compactación de eventos, y confirmación de tools para HITL — más superficie propia que mantener y probar en el plazo del reto.
- Curva de integración con Postgres y con el mecanismo de confirmación equivalente al de ADK no está tan directa para el tiempo disponible.
- Descartada para este alcance: mayor esfuerzo de integración sin ventaja clara dado que el reto ya usa el ecosistema Google (Gemini) y valora un framework de agentes dedicado.

### Google ADK 2.x (elegida)
- `Runner` + `DatabaseSessionService` dan memoria persistente en Postgres sin código propio de bajo nivel.
- `EventsCompactionConfig` resuelve control de tamaño de historial sin recortar `contents` a mano (evita romper firmas de pensamiento de Gemini 3 en function calling).
- Confirmación de tools nativa cubre el HITL primario (aunque experimental — mitigado con fallback, ver ADR-002).
- Integra bien con OpenTelemetry vía `openinference-instrumentation-google-adk` → Langfuse.
- Contras aceptados: paquete relativamente nuevo (API 2.x cambió respecto a 1.x), algunas features (confirmación de tools) son experimentales, y no se puede escribir de memoria — cada firma se verifica contra el paquete instalado (regla operativa del proyecto, no solo de esta decisión).

## Decisión

Google ADK 2.x para el núcleo decisional (`Agent` "Luis" + 3 tools + plugins de guardrails), con FastAPI propio exponiendo SSE sobre `runner.run_async` (no `adk api_server`, para tener control total del contrato HTTP definido en `02-api-contract.md`).

## Consecuencias

- Cada clase/firma de ADK usada en el código (F2 en adelante) se verifica contra el paquete instalado antes de escribirse; se documenta en `specs/notes/adk-api.md`.
- La confirmación de tools (experimental) empieza con un spike corto en F3; si no queda estable sobre SSE propio, se usa el fallback documentado en ADR-002 sin bloquear la fase.
- Si ADK 2.x deprecara o rompiera `DatabaseSessionService`/`EventsCompactionConfig` en una versión futura, el puerto `LlmProvider` y la separación `domain`/`agent` (spec 01) acotan el blast radius: solo `agent/` e `infrastructure/` deberían tocarse, no `domain/` ni `application/`.
