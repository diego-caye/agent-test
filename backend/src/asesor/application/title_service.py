import logging
import re
from uuid import UUID

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.genai import types

from asesor.infrastructure.db.session_title_repository import SqlSessionTitleRepository

logger = logging.getLogger(__name__)

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

    El título vive en su propia tabla (session_title_repository), no en el
    estado de la sesión de ADK: guardarlo ahí competía por el mismo lock
    optimista que el turno de chat, y un turno siguiente que llegara mientras
    el título se escribía salía rechazado con StaleSessionError — un adorno
    tumbando la respuesta real (visto en producción, no en teoría).
    """

    def __init__(self, model: BaseLlm, titles: SqlSessionTitleRepository) -> None:
        self._model = model
        self._titles = titles

    async def ensure_title(self, user_id: UUID, session_id: str, first_message: str) -> str | None:
        if await self._titles.get(session_id) is not None:
            return None

        title = await self._generate(first_message) or fallback_title(first_message)
        await self._titles.upsert(session_id, user_id, title)
        return title

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
