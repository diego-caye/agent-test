from uuid import UUID

from sqlalchemy import select

from asesor.domain.entities import Handoff
from asesor.domain.enums import CanalPreferido, HandoffStatus, MotivoHandoff, Urgencia
from asesor.infrastructure.db.engine import SessionFactory
from asesor.infrastructure.db.models import HandoffRow


def _to_domain(row: HandoffRow) -> Handoff:
    return Handoff(
        id=row.id,
        session_id=row.session_id,
        user_id=row.user_id,
        motivo=MotivoHandoff(row.motivo),
        resumen_requerimiento=row.resumen_requerimiento,
        canal_preferido=CanalPreferido(row.canal_preferido) if row.canal_preferido else None,
        urgencia=Urgencia(row.urgencia) if row.urgencia else None,
        status=HandoffStatus(row.status),
        created_at=row.created_at,
    )


class SqlHandoffRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def find_open(self, session_id: str) -> Handoff | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(HandoffRow).where(
                    HandoffRow.session_id == session_id,
                    HandoffRow.status == HandoffStatus.OPEN.value,
                )
            )
            return _to_domain(row) if row else None

    async def get(self, handoff_id: int) -> Handoff | None:
        async with self._session_factory() as session:
            row = await session.get(HandoffRow, handoff_id)
            return _to_domain(row) if row else None

    async def create(
        self,
        *,
        session_id: str,
        user_id: UUID,
        motivo: MotivoHandoff,
        resumen_requerimiento: str,
        canal_preferido: CanalPreferido | None,
        urgencia: Urgencia | None,
    ) -> Handoff:
        async with self._session_factory() as session, session.begin():
            row = HandoffRow(
                session_id=session_id,
                user_id=user_id,
                motivo=motivo.value,
                resumen_requerimiento=resumen_requerimiento,
                canal_preferido=canal_preferido.value if canal_preferido else None,
                urgencia=urgencia.value if urgencia else None,
                status=HandoffStatus.OPEN.value,
            )
            session.add(row)
            await session.flush()
            return _to_domain(row)

    async def list(self, status: HandoffStatus | None = None) -> list[Handoff]:
        statement = select(HandoffRow).order_by(HandoffRow.created_at.desc())
        if status is not None:
            statement = statement.where(HandoffRow.status == status.value)

        async with self._session_factory() as session:
            rows = (await session.scalars(statement)).all()
            return [_to_domain(row) for row in rows]

    async def set_status(self, handoff_id: int, status: HandoffStatus) -> Handoff:
        async with self._session_factory() as session, session.begin():
            row = await session.get(HandoffRow, handoff_id, with_for_update=True)
            if row is None:
                raise LookupError(handoff_id)
            row.status = status.value
            await session.flush()
            return _to_domain(row)
