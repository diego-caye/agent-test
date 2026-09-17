import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from google.adk.models import Gemini
from google.adk.models.base_llm import BaseLlm
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, DatabaseSessionService
from sqlalchemy.ext.asyncio import AsyncEngine

from asesor.agent.factory import APP_NAME, create_adk_app, create_agent
from asesor.application.evaluation_service import EvaluationService
from asesor.application.handoff_service import HandoffService
from asesor.application.knowledge_service import KnowledgeService
from asesor.application.lead_service import LeadService
from asesor.application.title_service import TitleService
from asesor.config import (
    DEFAULT_MODEL_ID,
    EmbeddingsProviderName,
    LlmProviderName,
    ModelChoice,
    Settings,
    UnknownModelError,
)
from asesor.domain.knowledge import EmbeddingsPort
from asesor.infrastructure.db.engine import create_engine, create_session_factory
from asesor.infrastructure.db.evaluation_repository import SqlEvaluationRepository
from asesor.infrastructure.db.feedback_repository import SqlFeedbackRepository
from asesor.infrastructure.db.handoff_repository import SqlHandoffRepository
from asesor.infrastructure.db.kb_repository import PgVectorRetriever
from asesor.infrastructure.db.lead_repository import SqlLeadRepository
from asesor.infrastructure.db.session_title_repository import SqlSessionTitleRepository
from asesor.infrastructure.embeddings.gemini import GeminiEmbeddings
from asesor.infrastructure.embeddings.ollama import OllamaEmbeddings
from asesor.infrastructure.llm.ollama_discovery import OllamaModelInfo, discover_ollama_models
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
    session_titles: SqlSessionTitleRepository
    feedback: SqlFeedbackRepository
    evaluation_service: EvaluationService
    session_service: BaseSessionService
    runners: "RunnerRegistry"

    @property
    def runner(self) -> Runner:
        return self.runners.get(None)


def build_catalog(
    settings: Settings, discovered_ollama: Sequence[OllamaModelInfo]
) -> list[ModelChoice]:
    """El catálogo real del selector: lo declarado a mano (típicamente Gemini,
    la API sí necesita una key y no hay forma de "descubrirla" localmente) más
    lo que Ollama reporta tener instalado ahora mismo.

    Los modelos de Ollama no se declaran en MODEL_CHOICES: se descubren en el
    arranque (discover_ollama_models), así la lista nunca queda
    desincronizada de lo que de verdad hay *pulled* — ni incluye modelos de
    solo-embeddings, que ya vienen filtrados.
    """
    static = [
        choice for choice in settings.model_choices if choice.provider is not LlmProviderName.OLLAMA
    ]
    dynamic = [
        ModelChoice(
            id=info.name,
            label=info.name,
            provider=LlmProviderName.OLLAMA,
            model=f"ollama_chat/{info.name}",
            supports_tools=info.supports_tools,
            supports_thinking=info.supports_thinking,
        )
        for info in discovered_ollama
    ]
    catalog = [*static, *dynamic]

    if not catalog:
        catalog = [
            ModelChoice(
                id=DEFAULT_MODEL_ID,
                label=settings.agent_model,
                provider=settings.llm_provider,
                model=settings.agent_model,
            )
        ]

    return catalog


def _default_choice_id(catalog: Sequence[ModelChoice], settings: Settings) -> str:
    """El modelo configurado en AGENT_MODEL, si aparece en el catálogo.

    No es simplemente "la primera opción": con el catálogo de Ollama armado
    por descubrimiento, el orden depende de lo que el servidor haya listado,
    no de una intención declarada. Lo único estable es AGENT_MODEL.
    """
    agent_model = settings.agent_model.removeprefix("ollama_chat/")
    for option in catalog:
        if option.model.removeprefix("ollama_chat/") == agent_model:
            return option.id
    return catalog[0].id if catalog else DEFAULT_MODEL_ID


class RunnerRegistry:
    """Un Runner por modelo del catálogo, creado la primera vez que se pide.

    Los servicios de aplicación y el servicio de sesiones se comparten: lo único
    que cambia entre runners es el modelo que usa el agente, así que una
    conversación puede alternar de modelo sin perder su historial ni su ficha.
    """

    def __init__(
        self, build: Callable[[ModelChoice], Runner], settings: Settings, catalog: list[ModelChoice]
    ) -> None:
        self._build = build
        self._catalog = catalog
        self._default_id = _default_choice_id(catalog, settings)
        self._runners: dict[str, Runner] = {}

    @property
    def catalog(self) -> list[ModelChoice]:
        return self._catalog

    @property
    def default_id(self) -> str:
        return self._default_id

    def choice(self, model_id: str | None) -> ModelChoice:
        wanted = model_id or self._default_id
        for option in self._catalog:
            if option.id == wanted:
                return option
        raise UnknownModelError(wanted)

    def get(self, model_id: str | None) -> Runner:
        option = self.choice(model_id)
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


def build_base_model(settings: Settings, choice: ModelChoice) -> BaseLlm:
    if choice.provider is LlmProviderName.OLLAMA:
        # El prefijo ollama_chat/ lo valida Settings para AGENT_MODEL y lo
        # arma build_catalog para el resto de opciones. think solo si la
        # propia opción soporta pensar (supports_thinking, descubierto en
        # vivo): mandárselo a un modelo sin esa capacidad devuelve 400 "does
        # not support thinking" (ADR-003) — antes se enviaba siempre.
        return LiteLlm(
            model=choice.model, **_ollama_kwargs(settings, think=choice.supports_thinking)
        )

    return Gemini(model=choice.model)


def build_fallback_model(settings: Settings, choice: ModelChoice) -> BaseLlm | None:
    if settings.fallback_model == choice.model:
        return None

    # El proveedor del respaldo lo dice el propio FALLBACK_MODEL (su prefijo
    # ollama_chat/), no el proveedor del modelo principal de este choice: son
    # independientes -- el catálogo mezcla opciones de Gemini y de Ollama
    # (spec 11), y FALLBACK_MODEL es uno solo, global, usado como respaldo
    # para cualquiera de ellas. Ramificar por choice.provider construía un
    # Gemini(model="ollama_chat/...") cuando el principal elegido era Gemini
    # y el respaldo configurado era de Ollama -- 404 real contra la API de
    # Gemini, visto en vivo al seleccionar Gemini desde el selector.
    if settings.fallback_model.startswith("ollama_chat/"):
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


def build_eval_model(settings: Settings, model: str | BaseLlm | None = None) -> BaseLlm:
    """Juez de la evaluación post-turno en background (spec 08 S5): EVAL_MODEL,
    no el del agente -- es una tarea de clasificación, no de conversación.
    """
    if isinstance(model, BaseLlm):
        return model

    if settings.llm_provider is LlmProviderName.OLLAMA:
        return LiteLlm(model=settings.eval_model, **_ollama_kwargs(settings, think=False))

    return Gemini(model=settings.eval_model)


def build_llm(settings: Settings, model: str | BaseLlm | None, choice: ModelChoice) -> BaseLlm:
    """Envuelve el modelo con reintentos y respaldo (spec 07 §3).

    Los tests inyectan su propio BaseLlm y también quedan envueltos, así el
    camino de reintento y fallback es el mismo que corre en producción.
    """
    if isinstance(model, BaseLlm):
        # En tests el respaldo es el mismo doble, para ejercitar el camino de
        # fallback sin necesitar un segundo modelo.
        return ResilientLlm(model=model.model, primary=model, fallback=model)

    primary = build_base_model(settings, choice)
    return ResilientLlm(
        model=primary.model, primary=primary, fallback=build_fallback_model(settings, choice)
    )


async def build_container(
    settings: Settings,
    session_service: BaseSessionService | None = None,
    model: str | BaseLlm | None = None,
    embeddings: EmbeddingsPort | None = None,
    title_model: BaseLlm | None = None,
    eval_model: BaseLlm | None = None,
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
    session_titles = SqlSessionTitleRepository(session_factory)
    # Un solo modelo ligero para las dos tareas de utilidad que no son la
    # conversación en sí (titular, resumir para compactar): construirlo dos
    # veces sería dos instancias de LiteLlm/Gemini idénticas sin motivo.
    utility_model = build_title_model(settings, title_model)
    title_service = TitleService(utility_model, session_titles)
    feedback = SqlFeedbackRepository(session_factory)
    evaluation_service = EvaluationService(
        build_eval_model(settings, eval_model), SqlEvaluationRepository(session_factory), settings
    )

    # Async y solo si hay OLLAMA_API_BASE: en los tests no se configura (usan
    # Gemini + un BaseLlm falso), así que esto no les pega a la red. Si Ollama
    # está apagado o tardando en arrancar, discover_ollama_models ya devuelve
    # [] en vez de tumbar el arranque del backend.
    discovered = (
        await discover_ollama_models(settings.ollama_api_base) if settings.ollama_api_base else []
    )
    catalog = build_catalog(settings, discovered)

    def build_runner(choice: ModelChoice) -> Runner:
        agent = create_agent(
            settings,
            lead_service,
            handoff_service,
            knowledge_service,
            build_llm(settings, model, choice),
        )
        return Runner(app=create_adk_app(settings, agent, utility_model), session_service=sessions)

    return Container(
        settings=settings,
        engine=engine,
        lead_service=lead_service,
        handoff_service=handoff_service,
        knowledge_service=knowledge_service,
        title_service=title_service,
        session_titles=session_titles,
        feedback=feedback,
        evaluation_service=evaluation_service,
        session_service=sessions,
        runners=RunnerRegistry(build_runner, settings, catalog),
    )


async def close_container(container: Container) -> None:
    await container.runners.close()
    await container.engine.dispose()


__all__ = ["APP_NAME", "Container", "build_container", "build_embeddings", "close_container"]
