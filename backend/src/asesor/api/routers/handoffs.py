from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from asesor.api.dtos import HandoffDto, UpdateHandoffRequest
from asesor.api.errors import ConflictError, NotFoundError, UnauthorizedError
from asesor.application.handoff_service import (
    HandoffNotFoundError,
    InvalidHandoffTransitionError,
)
from asesor.domain.entities import Handoff
from asesor.domain.enums import HandoffStatus
from asesor.infrastructure.container import Container

router = APIRouter(prefix="/api/v1/handoffs", tags=["handoffs"])


def require_admin(request: Request, authorization: Annotated[str | None, Header()] = None) -> None:
    container: Container = request.app.state.container
    expected = f"Bearer {container.settings.admin_token}"
    if not authorization or authorization != expected:
        raise UnauthorizedError("Admin token required")


Admin = Annotated[None, Depends(require_admin)]


def _to_dto(handoff: Handoff) -> HandoffDto:
    return HandoffDto(
        id=handoff.id,
        ticket=handoff.ticket,
        session_id=handoff.session_id,
        user_id=handoff.user_id,
        motivo=handoff.motivo.value,
        resumen_requerimiento=handoff.resumen_requerimiento,
        canal_preferido=handoff.canal_preferido.value if handoff.canal_preferido else None,
        urgencia=handoff.urgencia.value if handoff.urgencia else None,
        status=handoff.status.value,
        created_at=handoff.created_at,
    )


@router.get("", response_model=list[HandoffDto])
async def list_handoffs(
    request: Request, _: Admin, status: HandoffStatus | None = None
) -> list[HandoffDto]:
    container: Container = request.app.state.container
    handoffs = await container.handoff_service.list(status)
    return [_to_dto(handoff) for handoff in handoffs]


@router.patch("/{handoff_id}", response_model=HandoffDto)
async def update_handoff(
    request: Request, _: Admin, handoff_id: int, body: UpdateHandoffRequest
) -> HandoffDto:
    container: Container = request.app.state.container
    try:
        handoff = await container.handoff_service.change_status(
            handoff_id, HandoffStatus(body.status)
        )
    except HandoffNotFoundError as exc:
        raise NotFoundError(exc.message) from exc
    except InvalidHandoffTransitionError as exc:
        raise ConflictError(exc.message) from exc

    return _to_dto(handoff)
