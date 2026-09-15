from dataclasses import dataclass

from google.adk.models.base_llm import BaseLlm
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, DatabaseSessionService
from sqlalchemy.ext.asyncio import AsyncEngine

from asesor.agent.factory import APP_NAME, create_adk_app, create_agent
from asesor.application.lead_service import LeadService
from asesor.config import Settings
from asesor.infrastructure.db.engine import create_engine, create_session_factory
from asesor.infrastructure.db.lead_repository import SqlLeadRepository


@dataclass(slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    lead_service: LeadService
    session_service: BaseSessionService
    runner: Runner


def build_container(
    settings: Settings,
    session_service: BaseSessionService | None = None,
    model: str | BaseLlm | None = None,
) -> Container:
    engine = create_engine(settings.database_url)
    lead_service = LeadService(SqlLeadRepository(create_session_factory(engine)))

    sessions = session_service or DatabaseSessionService(db_url=settings.database_url)
    agent = create_agent(settings, lead_service, model)
    runner = Runner(
        app=create_adk_app(settings, agent),
        session_service=sessions,
    )

    return Container(
        settings=settings,
        engine=engine,
        lead_service=lead_service,
        session_service=sessions,
        runner=runner,
    )


async def close_container(container: Container) -> None:
    await container.runner.close()
    await container.engine.dispose()


__all__ = ["APP_NAME", "Container", "build_container", "close_container"]
