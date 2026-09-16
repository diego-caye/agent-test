import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header, Request
from fastapi.responses import StreamingResponse
from google.adk.events import Event

from asesor.agent.guardrails.faults import parse_fault
from asesor.api.dependencies import UserId
from asesor.api.dtos import ChatRequest, ConfirmationRequest
from asesor.api.errors import AppError, NotFoundError
from asesor.api.sse import SseEvent, translate
from asesor.application.chat_service import ChatService, SessionNotFoundError
from asesor.config import UnknownModelError
from asesor.infrastructure.container import Container
from asesor.infrastructure.telemetry import log_turn, turn_span

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


async def _stream(
    container: Container,
    session_id: str,
    user_id: UUID,
    events: AsyncIterator[Event],
) -> AsyncIterator[str]:
    with turn_span(
        session_id=session_id, user_id=str(user_id), settings=container.settings
    ) as turn:
        completed: dict[str, Any] = {}
        reported_error = False

        try:
            async for sse_event in translate(events, turn.trace_id):
                if sse_event.event == "message.completed":
                    completed = dict(sse_event.data)
                reported_error = reported_error or sse_event.event == "error"
                yield sse_event.encode()
        except Exception:
            logger.exception("chat turn failed", extra={"trace_id": turn.trace_id})
            turn.set("error", True)
            if not reported_error:
                yield SseEvent(
                    "error",
                    {
                        "code": "UPSTREAM_UNAVAILABLE",
                        "message": (
                            "No pudimos conectar con el asesor. Reintenta en unos segundos."
                        ),
                        "retryable": True,
                    },
                ).encode()
            return

        turn.set("tokens_in", int(completed.get("tokens_in", 0) or 0))
        turn.set("tokens_out", int(completed.get("tokens_out", 0) or 0))
        turn.set("latency_ms", int(completed.get("latency_ms", 0) or 0))

        log_turn(
            {
                "event": "chat.turn",
                "session_id": session_id,
                "user_id": str(user_id),
                "provider": container.settings.llm_provider.value,
                **completed,
            }
        )


async def _guarded_service(
    request: Request, user_id: UUID, session_id: str, model_id: str | None = None
) -> ChatService:
    container: Container = request.app.state.container

    try:
        runner = container.runners.get(model_id)
    except UnknownModelError as exc:
        raise AppError("UNKNOWN_MODEL", str(exc), http_status=422) from exc

    service = ChatService(runner, container.session_service)
    try:
        await service.get_session(user_id, session_id)
    except SessionNotFoundError as exc:
        raise NotFoundError("Session not found") from exc
    return service


@router.post("/stream")
async def chat_stream(
    request: Request,
    user_id: UserId,
    body: ChatRequest,
    background: BackgroundTasks,
    x_debug_fault: Annotated[str | None, Header()] = None,
) -> StreamingResponse:
    container: Container = request.app.state.container
    service = await _guarded_service(request, user_id, body.session_id, body.model_id)

    # El header se ignora fuera de dev, aunque venga (spec 07 §4).
    fault = parse_fault(x_debug_fault) if container.settings.fault_injection_active else None

    # En segundo plano: titular la conversación no debe sumar latencia al turno
    # ni romperlo si el modelo ligero falla.
    background.add_task(
        container.title_service.ensure_title, str(user_id), body.session_id, body.message
    )

    events = service.run_turn(user_id, body.session_id, body.message, fault)
    return StreamingResponse(
        _stream(container, body.session_id, user_id, events),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
        background=background,
    )


@router.post("/confirmations")
async def chat_confirmation(
    request: Request, user_id: UserId, body: ConfirmationRequest
) -> StreamingResponse:
    container: Container = request.app.state.container
    service = await _guarded_service(request, user_id, body.session_id, body.model_id)

    events = service.resume_with_confirmation(
        user_id, body.session_id, body.confirmation_id, body.approved
    )
    return StreamingResponse(
        _stream(container, body.session_id, user_id, events),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
