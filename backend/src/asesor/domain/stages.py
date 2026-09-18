from asesor.domain.entities import Lead
from asesor.domain.enums import NivelInteres, Stage

_FORWARD_ORDER: tuple[Stage, ...] = (
    Stage.NUEVO,
    Stage.DESCUBRIMIENTO,
    Stage.INTERES_CONCRETO,
    Stage.DERIVACION_PENDIENTE,
    Stage.DERIVADO,
)

_HITL_STAGES = frozenset({Stage.DERIVACION_PENDIENTE, Stage.DERIVADO})


def has_concrete_interest(lead: Lead) -> bool:
    if lead.nivel_interes is NivelInteres.ALTO:
        return True
    knows_vehicle = lead.tipo_vehiculo_interes is not None or lead.motorizacion_interes is not None
    return lead.uso_principal is not None and knows_vehicle


def stage_from_lead(lead: Lead) -> Stage:
    if has_concrete_interest(lead):
        return Stage.INTERES_CONCRETO
    if lead.nombre:
        return Stage.DESCUBRIMIENTO
    return Stage.NUEVO


def next_stage(current: Stage, lead: Lead) -> Stage:
    if current in _HITL_STAGES:
        return current

    derived = stage_from_lead(lead)
    if _FORWARD_ORDER.index(derived) > _FORWARD_ORDER.index(current):
        return derived
    return current
