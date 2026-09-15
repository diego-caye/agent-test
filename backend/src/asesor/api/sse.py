import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from google.adk.events import Event

from asesor.domain.enums import ToolStatus

logger = logging.getLogger(__name__)

LEAD_TOOL_NAME = "guardar_lead"
HANDOFF_TOOL_NAME = "solicitar_contacto_humano"
CONFIRMATION_CALL_NAME = "adk_request_confirmation"
UPSTREAM_ERROR_MESSAGE = "No pudimos generar la respuesta. Reintenta en unos segundos."


@dataclass(frozen=True, slots=True)
class SseEvent:
    event: str
    data: dict[str, Any]

    def encode(self) -> str:
        payload = json.dumps(self.data, ensure_ascii=False, default=str)
        return f"event: {self.event}\ndata: {payload}\n\n"


@dataclass(slots=True)
class TurnMetrics:
    started_at: float = field(default_factory=time.perf_counter)
    tokens_in: int = 0
    tokens_out: int = 0
    model: str | None = None

    def observe(self, event: Event) -> None:
        usage = event.usage_metadata
        if usage is not None:
            self.tokens_in += usage.prompt_token_count or 0
            self.tokens_out += usage.candidates_token_count or 0
        if event.model_version:
            self.model = event.model_version

    @property
    def latency_ms(self) -> int:
        return int((time.perf_counter() - self.started_at) * 1000)


def _confirmation_event(call: Any) -> SseEvent:
    """Traduce el adk_request_confirmation de ADK al contrato de spec 02."""
    args = dict(call.args or {})
    payload = dict((args.get("toolConfirmation") or {}).get("payload") or {})
    return SseEvent(
        "hitl.confirmation_required",
        {
            "confirmation_id": call.id,
            "motivo": payload.get("motivo"),
            "resumen": payload.get("resumen"),
            "canal_preferido": payload.get("canal_preferido"),
            "urgencia": payload.get("urgencia"),
        },
    )


def _text_of(event: Event) -> str:
    if event.content is None or not event.content.parts:
        return ""
    return "".join(part.text or "" for part in event.content.parts)


async def translate(events: AsyncIterator[Event], trace_id: str) -> AsyncIterator[SseEvent]:
    metrics = TurnMetrics()
    tool_started_at: dict[str, float] = {}
    streamed_any_delta = False
    last_text = ""
    last_event_id = ""

    async for event in events:
        metrics.observe(event)
        last_event_id = event.id or last_event_id

        if event.error_code:
            # El detalle del proveedor puede traer endpoints, claves o trazas:
            # va al log, nunca al cliente.
            logger.warning(
                "upstream error %s: %s",
                event.error_code,
                event.error_message,
                extra={"trace_id": trace_id},
            )
            yield SseEvent(
                "error",
                {"code": event.error_code, "message": UPSTREAM_ERROR_MESSAGE, "retryable": True},
            )
            continue

        for call in event.get_function_calls():
            if call.name == CONFIRMATION_CALL_NAME:
                yield _confirmation_event(call)
                continue
            tool_started_at[call.name or ""] = time.perf_counter()
            yield SseEvent("tool.started", {"name": call.name})

        for response in event.get_function_responses():
            name = response.name or ""
            started = tool_started_at.pop(name, None)
            duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
            payload = response.response if isinstance(response.response, dict) else {}
            status = str(payload.get("status", ToolStatus.OK.value))

            yield SseEvent(
                "tool.finished",
                {"name": name, "status": status, "duration_ms": duration_ms},
            )

            data = payload.get("data") or {}

            if name == LEAD_TOOL_NAME and status == ToolStatus.OK.value:
                yield SseEvent(
                    "lead.updated",
                    {"lead": data.get("lead"), "etapa": data.get("etapa")},
                )

            if name == HANDOFF_TOOL_NAME and data.get("handoff_id"):
                yield SseEvent(
                    "handoff.created",
                    {
                        "handoff_id": data.get("handoff_id"),
                        "ticket": data.get("ticket"),
                        "motivo": data.get("motivo"),
                        "status": data.get("status"),
                        "ya_existia": data.get("ya_existia", False),
                    },
                )

        text = _text_of(event)
        if text:
            if event.partial:
                streamed_any_delta = True
                yield SseEvent("message.delta", {"delta": text})
            else:
                last_text = text

    if not streamed_any_delta and last_text:
        yield SseEvent("message.delta", {"delta": last_text})

    yield SseEvent(
        "message.completed",
        {
            "message_id": last_event_id,
            "trace_id": trace_id,
            "latency_ms": metrics.latency_ms,
            "tokens_in": metrics.tokens_in,
            "tokens_out": metrics.tokens_out,
            "model": metrics.model,
        },
    )
