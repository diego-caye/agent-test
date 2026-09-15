import asyncio
from enum import StrEnum
from typing import Any

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from asesor.agent.tools.envelope import error, no_results

FAULT_STATE_KEY = "temp:fault"


class Fault(StrEnum):
    TOOL_ERROR = "tool_error"
    MODEL_429 = "model_429"
    MODEL_TIMEOUT = "model_timeout"
    RAG_DOWN = "rag_down"


class InjectedModelError(RuntimeError):
    """Fallo del modelo provocado a propósito, para demostrar los fallbacks."""

    def __init__(self, fault: Fault) -> None:
        super().__init__(f"fault injection: {fault.value}")
        self.fault = fault


def parse_fault(raw: str | None) -> Fault | None:
    if not raw:
        return None
    try:
        return Fault(raw.strip().lower())
    except ValueError:
        return None


class FaultInjectionPlugin(BasePlugin):
    """Solo se registra si APP_ENV=dev y ENABLE_FAULT_INJECTION=true."""

    def __init__(self) -> None:
        super().__init__(name="fault-injection")

    # Los fallos del modelo NO se inyectan aquí: ADK captura las excepciones de
    # los plugins y las convierte en un error del turno, así que ResilientLlm
    # nunca vería el 429 ni podría caer al respaldo. Se inyectan dentro de
    # ResilientLlm, leyendo el contextvar de fault_context.

    async def before_tool_callback(
        self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext
    ) -> dict[str, Any] | None:
        fault = parse_fault(tool_context.state.get(FAULT_STATE_KEY))

        if fault is Fault.RAG_DOWN and tool.name == "search_knowledge_base":
            await asyncio.sleep(0)
            return no_results()

        if fault is Fault.TOOL_ERROR:
            return error(
                "TOOL_UNAVAILABLE",
                "La herramienta no está disponible en este momento",
                retryable=True,
            )

        return None
