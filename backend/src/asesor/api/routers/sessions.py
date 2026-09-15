from datetime import UTC, datetime

from fastapi import APIRouter, Request

from asesor.agent.parts import visible_text
from asesor.agent.state import read_dialog_state
from asesor.api.dependencies import UserId
from asesor.api.dtos import (
    CreateSessionResponse,
    LeadDto,
    LeadResponse,
    MessageDto,
    SessionSummary,
)
from asesor.api.errors import NotFoundError
from asesor.application.chat_service import ChatService, SessionNotFoundError
from asesor.infrastructure.container import Container

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def _container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def _chat_service(request: Request) -> ChatService:
    container = _container(request)
    return ChatService(container.runner, container.session_service)


@router.post("", response_model=CreateSessionResponse)
async def create_session(request: Request, user_id: UserId) -> CreateSessionResponse:
    session_id = await _chat_service(request).create_session(user_id)
    return CreateSessionResponse(session_id=session_id)


@router.get("", response_model=list[SessionSummary])
async def list_sessions(request: Request, user_id: UserId) -> list[SessionSummary]:
    sessions = await _chat_service(request).list_sessions(user_id)
    summaries = [
        SessionSummary(
            session_id=session.id,
            last_update_time=datetime.fromtimestamp(session.last_update_time, tz=UTC),
            etapa=read_dialog_state(session.state).stage.value,
        )
        for session in sessions
    ]
    return sorted(summaries, key=lambda s: s.last_update_time, reverse=True)


@router.get("/{session_id}/messages", response_model=list[MessageDto])
async def list_messages(request: Request, user_id: UserId, session_id: str) -> list[MessageDto]:
    try:
        session = await _chat_service(request).get_session(user_id, session_id)
    except SessionNotFoundError as exc:
        raise NotFoundError("Session not found") from exc

    messages: list[MessageDto] = []
    for event in session.events:
        if event.content is None:
            continue
        text = visible_text(event.content)
        if not text or event.partial:
            continue
        messages.append(
            MessageDto(
                role="user" if event.content.role == "user" else "agent",
                content=text,
                created_at=datetime.fromtimestamp(event.timestamp, tz=UTC),
            )
        )
    return messages


@router.get("/{session_id}/lead", response_model=LeadResponse)
async def get_lead(request: Request, user_id: UserId, session_id: str) -> LeadResponse:
    container = _container(request)
    try:
        session = await _chat_service(request).get_session(user_id, session_id)
    except SessionNotFoundError as exc:
        raise NotFoundError("Session not found") from exc

    dialog = read_dialog_state(session.state)
    snapshot = await container.lead_service.get_snapshot(user_id, dialog.stage)
    lead = snapshot.lead

    return LeadResponse(
        lead=LeadDto(
            nombre=lead.nombre,
            telefono=lead.telefono,
            email=lead.email,
            canal_preferido=lead.canal_preferido,
            consentimiento_contacto=lead.consentimiento_contacto,
            uso_principal=lead.uso_principal,
            tipo_vehiculo_interes=lead.tipo_vehiculo_interes,
            motorizacion_interes=lead.motorizacion_interes,
            nivel_interes=lead.nivel_interes,
        ),
        etapa=snapshot.stage.value,
        solo_mirando=dialog.solo_mirando,
    )
