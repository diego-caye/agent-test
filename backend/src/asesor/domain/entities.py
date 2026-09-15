from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID

from asesor.domain.enums import (
    CanalPreferido,
    Motorizacion,
    NivelInteres,
    Stage,
    TipoVehiculo,
    UsoPrincipal,
)


@dataclass(frozen=True, slots=True)
class Lead:
    user_id: UUID
    nombre: str | None = None
    telefono: str | None = None
    email: str | None = None
    canal_preferido: CanalPreferido | None = None
    consentimiento_contacto: bool = False
    uso_principal: UsoPrincipal | None = None
    tipo_vehiculo_interes: TipoVehiculo | None = None
    motorizacion_interes: Motorizacion | None = None
    nivel_interes: NivelInteres | None = None

    def merge(self, update: "LeadUpdate") -> "Lead":
        changes = {k: v for k, v in update.as_dict().items() if v is not None}
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class LeadUpdate:
    nombre: str | None = None
    telefono: str | None = None
    email: str | None = None
    canal_preferido: CanalPreferido | None = None
    consentimiento_contacto: bool | None = None
    uso_principal: UsoPrincipal | None = None
    tipo_vehiculo_interes: TipoVehiculo | None = None
    motorizacion_interes: Motorizacion | None = None
    nivel_interes: NivelInteres | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "nombre": self.nombre,
            "telefono": self.telefono,
            "email": self.email,
            "canal_preferido": self.canal_preferido,
            "consentimiento_contacto": self.consentimiento_contacto,
            "uso_principal": self.uso_principal,
            "tipo_vehiculo_interes": self.tipo_vehiculo_interes,
            "motorizacion_interes": self.motorizacion_interes,
            "nivel_interes": self.nivel_interes,
        }

    def is_empty(self) -> bool:
        return all(value is None for value in self.as_dict().values())

    def carries_contact_data(self) -> bool:
        return self.telefono is not None or self.email is not None


@dataclass(frozen=True, slots=True)
class DialogState:
    stage: Stage = Stage.NUEVO
    solo_mirando: bool = False
    stage_previa: Stage | None = None
