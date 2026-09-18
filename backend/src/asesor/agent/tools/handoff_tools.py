from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from google.adk.tools import ToolContext
from pydantic import BaseModel, Field, ValidationError

from asesor.agent.state import STAGE_KEY, STAGE_PREVIA_KEY, read_dialog_state
from asesor.agent.tools.envelope import error, ok
from asesor.application.handoff_service import HandoffService
from asesor.domain.enums import CanalPreferido, MotivoHandoff, Stage, Urgencia
from asesor.domain.errors import DomainError

SolicitarContactoHumano = Callable[..., Awaitable[dict[str, Any]]]

CONFIRMATION_HINT = "¿Confirmas que derivemos tu solicitud a un asesor humano?"


class _HandoffArgs(BaseModel):
    motivo: MotivoHandoff
    resumen_requerimiento: str = Field(min_length=10, max_length=500)
    canal_preferido: CanalPreferido | None = None
    urgencia: Urgencia | None = None


def make_solicitar_contacto_humano(handoff_service: HandoffService) -> SolicitarContactoHumano:
    async def solicitar_contacto_humano(
        tool_context: ToolContext,
        motivo: str,
        resumen_requerimiento: str,
        canal_preferido: str | None = None,
        urgencia: str | None = None,
    ) -> dict[str, Any]:
        """Deriva al usuario a un asesor humano, con su confirmación previa.

        Úsala cuando el usuario pida un test drive o una cotización formal, quiera
        comprar y hablar con una persona, exprese disconformidad, o el tema supere
        lo que puedes orientar. El usuario debe confirmar antes de que se ejecute.

        Args:
            motivo: Uno de TEST_DRIVE, COTIZACION_FORMAL, COMPRA_INMEDIATA,
                DISCONFORMIDAD, FUERA_DE_ALCANCE.
            resumen_requerimiento: Resumen de lo que necesita, 10 a 500 caracteres.
            canal_preferido: Uno de WHATSAPP, LLAMADA, EMAIL, CHAT.
            urgencia: Una de BAJA, MEDIA, ALTA.

        Returns:
            El estado de la solicitud y su número de ticket cuando se crea.
        """
        try:
            args = _HandoffArgs(
                motivo=motivo,
                resumen_requerimiento=resumen_requerimiento,
                canal_preferido=canal_preferido,
                urgencia=urgencia,
            )
        except ValidationError as exc:
            first = exc.errors()[0]
            field = ".".join(str(part) for part in first["loc"])
            return error("VALIDATION_ERROR", f"{field}: {first['msg']}")

        session_id = tool_context.session.id
        dialog = read_dialog_state(tool_context.state)
        confirmation = tool_context.tool_confirmation

        if confirmation is None:
            tool_context.state[STAGE_PREVIA_KEY] = dialog.stage.value
            tool_context.state[STAGE_KEY] = Stage.DERIVACION_PENDIENTE.value
            tool_context.request_confirmation(
                hint=CONFIRMATION_HINT,
                payload={
                    "motivo": args.motivo.value,
                    "resumen": args.resumen_requerimiento,
                    "canal_preferido": args.canal_preferido.value if args.canal_preferido else None,
                    "urgencia": args.urgencia.value if args.urgencia else None,
                },
            )
            return ok({"pendiente_de_confirmacion": True})

        if not confirmation.confirmed:
            tool_context.state[STAGE_KEY] = (
                tool_context.state.get(STAGE_PREVIA_KEY) or Stage.NUEVO.value
            )
            return ok({"cancelado": True})

        try:
            handoff, created = await handoff_service.open_or_get(
                session_id=session_id,
                user_id=UUID(tool_context.user_id),
                motivo=args.motivo,
                resumen_requerimiento=args.resumen_requerimiento,
                canal_preferido=args.canal_preferido,
                urgencia=args.urgencia,
            )
        except DomainError as exc:
            return error(exc.code, exc.message, retryable=exc.retryable)

        tool_context.state[STAGE_KEY] = Stage.DERIVADO.value

        return ok(
            {
                "handoff_id": handoff.id,
                "ticket": handoff.ticket,
                "motivo": handoff.motivo.value,
                "status": handoff.status.value,
                "ya_existia": not created,
            }
        )

    return solicitar_contacto_humano
