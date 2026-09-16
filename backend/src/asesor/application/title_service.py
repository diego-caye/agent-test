import logging
import re

from google.adk.events import Event
from google.adk.events.event_actions import EventActions
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.sessions import BaseSessionService, Session
from google.genai import types

from asesor.agent.factory import APP_NAME

logger = logging.getLogger(__name__)

TITLE_STATE_KEY = "titulo"
MAX_TITLE_CHARS = 48

_PROMPT = (
    "Resume en un titulo corto de 3 a 6 palabras de que trata esta consulta de "
    "un cliente a un asesor automotriz. Responde SOLO el titulo, sin comillas, "
    "sin punto final y sin explicaciones.\n\nConsulta: {mensaje}\n\nTitulo:"
)

_QUOTES = re.compile(r'^["\'`¿¡\s]+|["\'`.\s]+$')
_WHITESPACE = re.compile(r"\s+")


def clean_title(raw: str) -> str:
    """Los modelos pequeños añaden comillas, prefijos y explicaciones de más."""
    first_line = next((line for line in raw.splitlines() if line.strip()), "")
    without_prefix = re.sub(r"^\s*(t[ií]tulo|title)\s*:\s*", "", first_line, flags=re.IGNORECASE)
    collapsed = _WHITESPACE.sub(" ", _QUOTES.sub("", without_prefix))
    return collapsed[:MAX_TITLE_CHARS].strip()


def fallback_title(message: str) -> str:
    """Si el modelo no da nada usable, el propio mensaje sirve de título."""
    collapsed = _WHITESPACE.sub(" ", message).strip()
    if len(collapsed) <= MAX_TITLE_CHARS:
        return collapsed
    return collapsed[: MAX_TITLE_CHARS - 1].rstrip() + "…"


class TitleService:
    """Pone nombre a la conversación a partir del primer mensaje del usuario.

    Corre en segundo plano y con el modelo ligero: nunca debe sumar latencia al
    turno ni romperlo si falla, porque es un adorno de la barra lateral.
    """

    def __init__(self, model: BaseLlm, session_service: BaseSessionService) -> None:
        self._model = model
        self._session_service = session_service

    async def ensure_title(self, user_id: str, session_id: str, first_message: str) -> str | None:
        """La sesión se recarga aquí, no se recibe ya cargada.

        Esto corre después del turno, así que una copia tomada antes estaría
        obsoleta y ADK rechazaría el append con StaleSessionError.
        """
        session = await self._load(user_id, session_id)
        if session is None or session.state.get(TITLE_STATE_KEY):
            return None

        title = await self._generate(first_message) or fallback_title(first_message)

        fresh = await self._load(user_id, session_id)
        if fresh is None:
            return None

        await self._store(fresh, title)
        return title

    async def _load(self, user_id: str, session_id: str) -> Session | None:
        return await self._session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

    async def _generate(self, message: str) -> str:
        request = LlmRequest(
            model=self._model.model,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=_PROMPT.format(mensaje=message))],
                )
            ],
        )

        try:
            chunks: list[str] = []
            async for response in self._model.generate_content_async(request, False):
                if response.partial or response.content is None or not response.content.parts:
                    continue
                chunks.extend(
                    part.text or "" for part in response.content.parts if not part.thought
                )
            return clean_title("".join(chunks))
        except Exception:
            logger.warning("no se pudo generar el título de la conversación", exc_info=True)
            return ""

    async def _store(self, session: Session, title: str) -> None:
        # El estado de sesión solo se puede cambiar añadiendo un evento con su
        # state_delta; no hay una API para escribirlo directamente.
        await self._session_service.append_event(
            session,
            Event(
                author="system",
                invocation_id="",
                actions=EventActions(state_delta={TITLE_STATE_KEY: title}),
            ),
        )
