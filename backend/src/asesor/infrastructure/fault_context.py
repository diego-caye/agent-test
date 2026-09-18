from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from asesor.agent.guardrails.faults import Fault

# Request-scoped: el header X-Debug-Fault llega al router, pero el modelo y las
# tools corren varias capas más abajo. Un contextvar los alcanza sin ensuciar las
# firmas de ADK, y se aísla solo por turno (importa con sesiones concurrentes).
_active_fault: ContextVar[Fault | None] = ContextVar("active_fault", default=None)


@contextmanager
def use_fault(fault: Fault | None) -> Iterator[None]:
    token = _active_fault.set(fault)
    try:
        yield
    finally:
        _active_fault.reset(token)


def current_fault() -> Fault | None:
    return _active_fault.get()
