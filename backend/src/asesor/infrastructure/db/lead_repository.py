from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from asesor.domain.entities import Lead, LeadUpdate
from asesor.domain.enums import (
    CanalPreferido,
    Motorizacion,
    NivelInteres,
    TipoVehiculo,
    UsoPrincipal,
)
from asesor.infrastructure.db.engine import SessionFactory
from asesor.infrastructure.db.models import LeadRow


def _to_domain(row: LeadRow) -> Lead:
    return Lead(
        user_id=row.user_id,
        nombre=row.nombre,
        telefono=row.telefono,
        email=row.email,
        canal_preferido=CanalPreferido(row.canal_preferido) if row.canal_preferido else None,
        consentimiento_contacto=row.consentimiento_contacto,
        uso_principal=UsoPrincipal(row.uso_principal) if row.uso_principal else None,
        tipo_vehiculo_interes=(
            TipoVehiculo(row.tipo_vehiculo_interes) if row.tipo_vehiculo_interes else None
        ),
        motorizacion_interes=(
            Motorizacion(row.motorizacion_interes) if row.motorizacion_interes else None
        ),
        nivel_interes=NivelInteres(row.nivel_interes) if row.nivel_interes else None,
    )


class SqlLeadRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def get(self, user_id: UUID) -> Lead | None:
        async with self._session_factory() as session:
            row = await session.scalar(select(LeadRow).where(LeadRow.user_id == user_id))
            return _to_domain(row) if row else None

    async def upsert(self, user_id: UUID, update: LeadUpdate) -> Lead:
        changes: dict[str, Any] = {
            key: (value.value if hasattr(value, "value") else value)
            for key, value in update.as_dict().items()
            if value is not None
        }

        async with self._session_factory() as session, session.begin():
            statement = (
                pg_insert(LeadRow)
                .values(user_id=user_id, **changes)
                .on_conflict_do_update(
                    index_elements=[LeadRow.user_id],
                    set_={**changes, "updated_at": func.now()},
                )
                .returning(LeadRow)
            )
            row = (await session.scalars(statement)).one()
            return _to_domain(row)
