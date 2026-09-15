from dataclasses import dataclass

from google.adk.models.base_llm import BaseLlm
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, DatabaseSessionService
from sqlalchemy.ext.asyncio import AsyncEngine

from asesor.agent.factory import APP_NAME, create_adk_app, create_agent
from asesor.application.handoff_service import HandoffService
from asesor.application.knowledge_service import KnowledgeService
from asesor.application.lead_service import LeadService
from asesor.config import EmbeddingsProviderName, Settings
from asesor.domain.knowledge import EmbeddingsPort
from asesor.infrastructure.db.engine import create_engine, create_session_factory
from asesor.infrastructure.db.handoff_repository import SqlHandoffRepository
from asesor.infrastructure.db.kb_repository import PgVectorRetriever
from asesor.infrastructure.db.lead_repository import SqlLeadRepository
from asesor.infrastructure.embeddings.gemini import GeminiEmbeddings


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
    raise NotImplementedError(
        f"EMBEDDINGS_PROVIDER={settings.embeddings_provider.value} llega en F8"
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
    agent = create_agent(settings, lead_service, handoff_service, knowledge_service, model)
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
