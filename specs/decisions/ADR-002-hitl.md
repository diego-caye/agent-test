# ADR-002 · Mecanismo de HITL

## Estado
Aceptado — camino primario confirmado por spike el 2026-09-15 (F3).

## Contexto

El reto exige HITL real: interrupción, derivación y confirmación asistida (spec 03 §3, spec 04 §2). El baseline n8n no tenía ninguno de los tres: su `solicitar_contacto_humano` terminaba en un `JSON.stringify` con un ticket de `Math.random`, sin pausa, sin cola humana y sin confirmación del usuario (brecha #6 de `00-baseline-analysis.md`).

`00-master-build.md` §8 marcaba la confirmación nativa de tools de ADK como **experimental** y pedía empezar F3 con un spike corto a través de nuestro propio SSE; si no quedaba limpio, había que caer a un fallback (`pending_confirmation` en estado de sesión, turno terminado, y la UI creando el handoff al confirmar).

## Opciones

### A. Confirmación nativa de tools de ADK (elegida)
La tool llama `tool_context.request_confirmation(hint=..., payload=...)`. ADK pausa el turno y emite una function call sintética `adk_request_confirmation` cuyos args llevan `originalFunctionCall` y el `toolConfirmation` con nuestro payload. Para reanudar, se manda una function response de rol `user`, con ese mismo nombre y el id de la llamada de confirmación, y ADK re-ejecuta la tool original con `tool_context.tool_confirmation` poblado.

### B. Fallback propio
La tool deja `pending_confirmation` en el estado de sesión y devuelve; el turno termina normal. `POST /chat/confirmations` crea el handoff directamente desde el servicio, sin volver a pasar por el agente, y arranca un turno nuevo para que el agente lo comunique.

## Spike

Se montó un `Runner` propio con `InMemorySessionService`, un `FakeAdkLlm` con guion y una tool de derivación, y se ejecutaron dos turnos:

1. **Turno 1.** El modelo llama `solicitar_contacto_humano`. La tool pide confirmación y devuelve. Observado: ADK emite la function call `adk_request_confirmation` con `originalFunctionCall` + `toolConfirmation` (incluyendo el payload con motivo y resumen), la tool responde `pending_confirmation`, y **el handoff no se crea**.
2. **Turno 2.** Se manda la function response con `confirmed=True` y el id de la confirmación. Observado: ADK **re-ejecuta la tool** con `tool_confirmation` poblado, la tool crea el handoff, y el agente produce su texto de cierre.

Resultado: el camino primario funciona sobre nuestro SSE, sin `adk api_server` y sin tocar el historial a mano.

Requisito descubierto en el spike: el `App` necesita `resumability_config=ResumabilityConfig(is_resumable=True)`; sin eso el turno no puede reanudarse.

## Decisión

**Opción A.** No se implementa el fallback: añadiría un segundo camino de código para el mismo caso de uso sin resolver nada que el primario no cubra.

Traducción a nuestro contrato (spec 02):
- `adk_request_confirmation` → SSE `hitl.confirmation_required {confirmation_id, motivo, resumen, canal_preferido, urgencia}`, donde `confirmation_id` es el id de esa function call y el resto sale del `payload` que la tool eligió.
- `POST /api/v1/chat/confirmations {session_id, confirmation_id, approved}` arma la function response y reanuda el stream con los mismos eventos que un turno normal.
- Aprobar ejecuta la tool y la etapa pasa a `DERIVADO`; cancelar (`approved=false`) devuelve la etapa a `stage_previa` y no crea nada.

## Consecuencias

- Dependemos de una feature marcada experimental por ADK. El riesgo está acotado: los AT-08, AT-09 y AT-10 cubren los tres caminos (confirmar, cancelar, segundo pedido idempotente), así que una regresión al subir de versión se detecta en CI, no en la demo.
- El formato de la respuesta de confirmación (`name = adk_request_confirmation`, el id de la llamada, `ToolConfirmation.model_dump()`) es un detalle interno de ADK 2.9.1. Está aislado en `ChatService.resume_with_confirmation` y documentado en `specs/notes/adk-api.md` §6, que es el único punto a tocar si cambia.
- La idempotencia del handoff no la da ADK: es un índice único parcial en Postgres (`ux_handoffs_one_open_per_session`, `WHERE status = 'OPEN'`) más el `open_or_get` del servicio, así que dos confirmaciones concurrentes no pueden crear dos tickets abiertos.
- Si ADK retirara la feature, la opción B sigue siendo viable y el punto de cambio está localizado; por eso no se descarta en este ADR, solo no se implementa hoy.
