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
from asesor.config import EmbeddingsProviderName, LlmProviderName, Settings
from asesor.domain.knowledge import EmbeddingsPort
from asesor.infrastructure.db.engine import create_engine, create_session_factory
from asesor.infrastructure.db.handoff_repository import SqlHandoffRepository
from asesor.infrastructure.db.kb_repository import PgVectorRetriever
from asesor.infrastructure.db.lead_repository import SqlLeadRepository
from asesor.infrastructure.embeddings.gemini import GeminiEmbeddings
from asesor.infrastructure.embeddings.ollama import OllamaEmbeddings
from asesor.infrastructure.llm.resilient import ResilientLlm


@dataclass(slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    lead_service: LeadService
    handoff_service: HandoffService
    knowledge_service: KnowledgeService
    session_service: BaseSessionService
    runner: Runner


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


def build_base_model(settings: Settings) -> BaseLlm:
    if settings.llm_provider is LlmProviderName.OLLAMA:
        # El prefijo ollama_chat/ ya viene en AGENT_MODEL y lo valida Settings.
        # num_ctx es obligatorio: sin él Ollama recorta el contexto en silencio.
        return LiteLlm(
            model=settings.agent_model,
            api_base=settings.ollama_api_base,
            num_ctx=settings.ollama_context_length,
            think=settings.ollama_think,
        )

    return Gemini(model=settings.agent_model)


def build_fallback_model(settings: Settings) -> BaseLlm | None:
    if settings.fallback_model == settings.agent_model:
        return None

    if settings.llm_provider is LlmProviderName.OLLAMA:
        return LiteLlm(
            model=settings.fallback_model,
            api_base=settings.ollama_api_base,
            num_ctx=settings.ollama_context_length,
            think=settings.ollama_think,
        )

    return Gemini(model=settings.fallback_model)


def build_llm(settings: Settings, model: str | BaseLlm | None) -> BaseLlm:
    """Envuelve el modelo con reintentos y respaldo (spec 07 §3).

    Los tests inyectan su propio BaseLlm y también quedan envueltos, así el
    camino de reintento y fallback es el mismo que corre en producción.
    """
    if isinstance(model, BaseLlm):
        # En tests el respaldo es el mismo doble, para ejercitar el camino de
        # fallback sin necesitar un segundo modelo.
        return ResilientLlm(model=model.model, primary=model, fallback=model)

    primary = build_base_model(settings)
    return ResilientLlm(
        model=primary.model, primary=primary, fallback=build_fallback_model(settings)
    )


def build_container(
    settings: Settings,
    session_service: BaseSessionService | None = None,
    model: str | BaseLlm | None = None,
    embeddings: EmbeddingsPort | None = None,
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
    agent = create_agent(
        settings, lead_service, handoff_service, knowledge_service, build_llm(settings, model)
    )
    runner = Runner(
        app=create_adk_app(settings, agent),
        session_service=sessions,
    )

    return Container(
        settings=settings,
        engine=engine,
        lead_service=lead_service,
        handoff_service=handoff_service,
        knowledge_service=knowledge_service,
        session_service=sessions,
        runner=runner,
    )


async def close_container(container: Container) -> None:
    await container.runner.close()
    await container.engine.dispose()


__all__ = ["APP_NAME", "Container", "build_container", "build_embeddings", "close_container"]
