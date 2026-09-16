import logging
from collections.abc import Callable
from dataclasses import dataclass

from google.adk.models import Gemini
from google.adk.models.base_llm import BaseLlm
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, DatabaseSessionService
from sqlalchemy.ext.asyncio import AsyncEngine

from asesor.agent.factory import APP_NAME, create_adk_app, create_agent
from asesor.application.handoff_service import HandoffService
from asesor.application.knowledge_service import KnowledgeService
from asesor.application.lead_service import LeadService
from asesor.application.title_service import TitleService
from asesor.config import EmbeddingsProviderName, LlmProviderName, ModelChoice, Settings
from asesor.domain.knowledge import EmbeddingsPort
from asesor.infrastructure.db.engine import create_engine, create_session_factory
from asesor.infrastructure.db.handoff_repository import SqlHandoffRepository
from asesor.infrastructure.db.kb_repository import PgVectorRetriever
from asesor.infrastructure.db.lead_repository import SqlLeadRepository
from asesor.infrastructure.embeddings.gemini import GeminiEmbeddings
from asesor.infrastructure.embeddings.ollama import OllamaEmbeddings
from asesor.infrastructure.llm.resilient import ResilientLlm

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    lead_service: LeadService
    handoff_service: HandoffService
    knowledge_service: KnowledgeService
    title_service: TitleService
    session_service: BaseSessionService
    runners: "RunnerRegistry"

    @property
    def runner(self) -> Runner:
        return self.runners.get(None)


class RunnerRegistry:
    """Un Runner por modelo del catálogo, creado la primera vez que se pide.

    Los servicios de aplicación y el servicio de sesiones se comparten: lo único
    que cambia entre runners es el modelo que usa el agente, así que una
    conversación puede alternar de modelo sin perder su historial ni su ficha.
    """

    def __init__(self, build: Callable[[ModelChoice], Runner], settings: Settings) -> None:
        self._build = build
        self._settings = settings
        self._runners: dict[str, Runner] = {}

    def get(self, model_id: str | None) -> Runner:
        option = self._settings.choice(model_id)
        if option.id not in self._runners:
            logger.info("creando runner para el modelo %s (%s)", option.id, option.model)
            self._runners[option.id] = self._build(option)
        return self._runners[option.id]

    async def close(self) -> None:
        for runner in self._runners.values():
            await runner.close()
        self._runners.clear()


def build_embeddings(settings: Settings) -> EmbeddingsPort:
    if settings.embeddings_provider is EmbeddingsProviderName.GEMINI:
        return GeminiEmbeddings(
            model=settings.embeddings_model,
            api_key=settings.google_api_key,
            use_vertexai=settings.google_genai_use_vertexai,
        )

    if settings.ollama_api_base is None:
        raise ValueError("EMBEDDINGS_PROVIDER=ollama requiere OLLAMA_API_BASE")

    return OllamaEmbeddings(model=settings.embeddings_model, api_base=settings.ollama_api_base)


def _ollama_kwargs(settings: Settings, *, think: bool) -> dict[str, object]:
    # num_ctx siempre: sin él Ollama recorta el contexto en silencio.
    kwargs: dict[str, object] = {
        "api_base": settings.ollama_api_base,
        "num_ctx": settings.ollama_context_length,
    }
    # think solo donde corresponde: mandárselo a un modelo sin esa capacidad
    # devuelve 400 "does not support thinking" (ADR-003).
    if think and settings.ollama_think is not None:
        kwargs["think"] = settings.ollama_think
    return kwargs


def build_base_model(settings: Settings, choice: ModelChoice | None = None) -> BaseLlm:
    option = choice or settings.choice(None)

    if option.provider is LlmProviderName.OLLAMA:
        # El prefijo ollama_chat/ lo valida Settings para AGENT_MODEL y lo
        # comprueba el catálogo para el resto de opciones.
        return LiteLlm(model=option.model, **_ollama_kwargs(settings, think=True))

    return Gemini(model=option.model)


def build_fallback_model(settings: Settings, choice: ModelChoice) -> BaseLlm | None:
    if settings.fallback_model == choice.model:
        return None

    if choice.provider is LlmProviderName.OLLAMA:
        # OLLAMA_THINK describe al modelo principal. El respaldo suele ser otro
        # más pequeño y sin esa capacidad, así que nunca se le envía.
        return LiteLlm(model=settings.fallback_model, **_ollama_kwargs(settings, think=False))

    return Gemini(model=settings.fallback_model)


def build_title_model(settings: Settings, model: str | BaseLlm | None = None) -> BaseLlm:
    """Modelo para titular conversaciones: el ligero, no el del agente.

    Es una tarea trivial y en segundo plano; gastar el modelo grande solo
    añadiría latencia y carga de GPU sin mejorar el resultado.
    """
    if isinstance(model, BaseLlm):
        return model

    if settings.llm_provider is LlmProviderName.OLLAMA:
        return LiteLlm(model=settings.guardrail_model, **_ollama_kwargs(settings, think=False))

    return Gemini(model=settings.guardrail_model)


def build_llm(
    settings: Settings, model: str | BaseLlm | None, choice: ModelChoice | None = None
) -> BaseLlm:
    """Envuelve el modelo con reintentos y respaldo (spec 07 §3).

    Los tests inyectan su propio BaseLlm y también quedan envueltos, así el
    camino de reintento y fallback es el mismo que corre en producción.
    """
    if isinstance(model, BaseLlm):
        # En tests el respaldo es el mismo doble, para ejercitar el camino de
        # fallback sin necesitar un segundo modelo.
        return ResilientLlm(model=model.model, primary=model, fallback=model)

    option = choice or settings.choice(None)
    primary = build_base_model(settings, option)
    return ResilientLlm(
        model=primary.model, primary=primary, fallback=build_fallback_model(settings, option)
    )


def build_container(
    settings: Settings,
    session_service: BaseSessionService | None = None,
    model: str | BaseLlm | None = None,
    embeddings: EmbeddingsPort | None = None,
    title_model: BaseLlm | None = None,
) -> Container:
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    lead_service = LeadService(SqlLeadRepository(session_factory))
    handoff_service = HandoffService(SqlHandoffRepository(session_factory))
    knowledge_service = KnowledgeService(
        embeddings or build_embeddings(settings),
        PgVectorRetriever(session_factory),
        settings.rag_min_score,
    )

    sessions = session_service or DatabaseSessionService(db_url=settings.database_url)
    title_service = TitleService(build_title_model(settings, title_model), sessions)

    def build_runner(choice: ModelChoice) -> Runner:
        agent = create_agent(
            settings,
            lead_service,
            handoff_service,
            knowledge_service,
            build_llm(settings, model, choice),
        )
        return Runner(app=create_adk_app(settings, agent), session_service=sessions)

    return Container(
        settings=settings,
        engine=engine,
        lead_service=lead_service,
        handoff_service=handoff_service,
        knowledge_service=knowledge_service,
        title_service=title_service,
        session_service=sessions,
        runners=RunnerRegistry(build_runner, settings),
    )


async def close_container(container: Container) -> None:
    await container.runners.close()
    await container.engine.dispose()


__all__ = ["APP_NAME", "Container", "build_container", "build_embeddings", "close_container"]
