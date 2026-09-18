from typing import Protocol
from uuid import UUID

from asesor.domain.entities import Handoff, can_transition
from asesor.domain.enums import CanalPreferido, HandoffStatus, MotivoHandoff, Urgencia
from asesor.domain.errors import DomainError


class InvalidHandoffTransitionError(DomainError):
    code = "CONFLICT"


class HandoffNotFoundError(DomainError):
    code = "NOT_FOUND"


class HandoffRepository(Protocol):
    async def find_open(self, session_id: str) -> Handoff | None: ...

    async def get(self, handoff_id: int) -> Handoff | None: ...

    async def create(
        self,
        *,
        session_id: str,
        user_id: UUID,
        motivo: MotivoHandoff,
        resumen_requerimiento: str,
        canal_preferido: CanalPreferido | None,
        urgencia: Urgencia | None,
    ) -> Handoff: ...

    async def list(self, status: HandoffStatus | None = None) -> list[Handoff]: ...

    async def set_status(self, handoff_id: int, status: HandoffStatus) -> Handoff: ...


class HandoffService:
    def __init__(self, repository: HandoffRepository) -> None:
        self._repository = repository

    async def open_or_get(
        self,
        *,
        session_id: str,
        user_id: UUID,
        motivo: MotivoHandoff,
        resumen_requerimiento: str,
        canal_preferido: CanalPreferido | None = None,
        urgencia: Urgencia | None = None,
    ) -> tuple[Handoff, bool]:
        """Return the handoff and whether it was created now (spec 03: idempotent)."""
        existing = await self._repository.find_open(session_id)
        if existing is not None:
            return existing, False

        created = await self._repository.create(
            session_id=session_id,
            user_id=user_id,
            motivo=motivo,
            resumen_requerimiento=resumen_requerimiento,
            canal_preferido=canal_preferido,
            urgencia=urgencia,
        )
        return created, True

    async def list(self, status: HandoffStatus | None = None) -> list[Handoff]:
        return await self._repository.list(status)

    async def change_status(self, handoff_id: int, target: HandoffStatus) -> Handoff:
        current = await self._repository.get(handoff_id)
        if current is None:
            raise HandoffNotFoundError(f"Handoff {handoff_id} not found")

        if not can_transition(current.status, target):
            raise InvalidHandoffTransitionError(
                f"Cannot move handoff {handoff_id} from {current.status} to {target}"
            )

        return await self._repository.set_status(handoff_id, target)
