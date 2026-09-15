import logging
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from asesor.api.dependencies import UserId
from asesor.api.dtos import ChatRequest
from asesor.api.errors import NotFoundError
from asesor.api.sse import SseEvent, translate
from asesor.application.chat_service import ChatService, SessionNotFoundError
from asesor.infrastructure.container import Container
from asesor.infrastructure.telemetry import log_turn, turn_span

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


async def _stream(
    container: Container, service: ChatService, user_id: UUID, body: ChatRequest
) -> AsyncIterator[str]:
    with turn_span(
        session_id=body.session_id, user_id=str(user_id), settings=container.settings
    ) as turn:
        events = service.run_turn(user_id, body.session_id, body.message)
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
                "session_id": body.session_id,
                "user_id": str(user_id),
                "provider": container.settings.llm_provider.value,
                **completed,
            }
        )


@router.post("/stream")
async def chat_stream(request: Request, user_id: UserId, body: ChatRequest) -> StreamingResponse:
    container: Container = request.app.state.container
    service = ChatService(container.runner, container.session_service)

    try:
        await service.get_session(user_id, body.session_id)
    except SessionNotFoundError as exc:
        raise NotFoundError("Session not found") from exc

    return StreamingResponse(
        _stream(container, service, user_id, body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
