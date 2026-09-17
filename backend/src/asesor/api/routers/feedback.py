from fastapi import APIRouter, Request

from asesor.api.dependencies import Admin, UserId
from asesor.api.dtos import FeedbackDto, FeedbackRequest, FeedbackResponse
from asesor.api.errors import NotFoundError
from asesor.application.chat_service import ChatService, SessionNotFoundError
from asesor.infrastructure.container import Container
from asesor.infrastructure.db.feedback_repository import FeedbackEntry
from asesor.infrastructure.telemetry import send_langfuse_score

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


def _container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def _to_dto(entry: FeedbackEntry) -> FeedbackDto:
    return FeedbackDto(
        id=entry.id,
        session_id=entry.session_id,
        trace_id=entry.trace_id,
        score=entry.score,
        message=entry.message,
        comment=entry.comment,
        created_at=entry.created_at,
    )


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: Request, user_id: UserId, body: FeedbackRequest
) -> FeedbackResponse:
    container = _container(request)

    try:
        await ChatService(container.runner, container.session_service).get_session(
            user_id, body.session_id
        )
    except SessionNotFoundError as exc:
        raise NotFoundError("Session not found") from exc

    await container.feedback.add(
        session_id=body.session_id,
        user_id=user_id,
        trace_id=body.trace_id,
        score=body.score,
        message=body.message,
        comment=body.comment,
    )

    # Best-effort: Langfuse permite adjuntar un score a un trace ya cerrado
    # (spec 08 S4). Si falla o no está configurado, el feedback ya quedó
    # guardado arriba -- nunca bloquea ni hace fallar el endpoint.
    await send_langfuse_score(
        container.settings,
        trace_id=body.trace_id,
        name="user-feedback",
        value=body.score,
        comment=body.comment,
    )

    return FeedbackResponse()


@router.get("", response_model=list[FeedbackDto])
async def list_feedback(request: Request, _: Admin, limit: int = 100) -> list[FeedbackDto]:
    container = _container(request)
    entries = await container.feedback.list(limit)
    return [_to_dto(entry) for entry in entries]
