from uuid import uuid4

import pytest

from asesor.domain.entities import Lead
from asesor.domain.enums import Motorizacion, NivelInteres, Stage, TipoVehiculo, UsoPrincipal
from asesor.domain.stages import next_stage, stage_from_lead

USER = uuid4()


def lead(**kwargs: object) -> Lead:
    return Lead(user_id=USER, **kwargs)  # type: ignore[arg-type]


def test_empty_lead_stays_nuevo() -> None:
    assert stage_from_lead(lead()) is Stage.NUEVO


def test_name_moves_to_descubrimiento() -> None:
    assert next_stage(Stage.NUEVO, lead(nombre="Diego")) is Stage.DESCUBRIMIENTO


def test_use_plus_vehicle_type_moves_to_interes_concreto() -> None:
    current = lead(
        nombre="Diego",
        uso_principal=UsoPrincipal.FAMILIA,
        tipo_vehiculo_interes=TipoVehiculo.SUV,
    )
    assert next_stage(Stage.DESCUBRIMIENTO, current) is Stage.INTERES_CONCRETO


def test_use_plus_motorizacion_also_moves_to_interes_concreto() -> None:
    current = lead(
        nombre="Diego",
        uso_principal=UsoPrincipal.CIUDAD,
        motorizacion_interes=Motorizacion.HIBRIDO,
    )
    assert next_stage(Stage.DESCUBRIMIENTO, current) is Stage.INTERES_CONCRETO


def test_use_alone_is_not_enough() -> None:
    current = lead(nombre="Diego", uso_principal=UsoPrincipal.CIUDAD)
    assert next_stage(Stage.DESCUBRIMIENTO, current) is Stage.DESCUBRIMIENTO


def test_high_interest_alone_moves_to_interes_concreto() -> None:
    current = lead(nombre="Diego", nivel_interes=NivelInteres.ALTO)
    assert next_stage(Stage.DESCUBRIMIENTO, current) is Stage.INTERES_CONCRETO


def test_machine_only_moves_forward() -> None:
    assert next_stage(Stage.INTERES_CONCRETO, lead()) is Stage.INTERES_CONCRETO
    assert next_stage(Stage.DESCUBRIMIENTO, lead()) is Stage.DESCUBRIMIENTO


def test_machine_may_skip_descubrimiento() -> None:
    anonymous_but_decided = lead(
        uso_principal=UsoPrincipal.TRABAJO,
        tipo_vehiculo_interes=TipoVehiculo.PICKUP,
    )
    assert next_stage(Stage.NUEVO, anonymous_but_decided) is Stage.INTERES_CONCRETO


@pytest.mark.parametrize("stage", [Stage.DERIVACION_PENDIENTE, Stage.DERIVADO])
def test_hitl_stages_are_never_recomputed_from_the_lead(stage: Stage) -> None:
    rich = lead(nombre="Diego", nivel_interes=NivelInteres.ALTO)
    assert next_stage(stage, rich) is stage
