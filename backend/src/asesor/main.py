from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.adk.models.base_llm import BaseLlm
from google.adk.sessions import BaseSessionService, DatabaseSessionService

from asesor.api.errors import register_error_handlers
from asesor.api.routers import chat, health, sessions
from asesor.config import Settings, get_settings
from asesor.infrastructure.container import build_container, close_container
from asesor.infrastructure.telemetry import setup_telemetry


def create_app(
    settings: Settings | None = None,
    session_service: BaseSessionService | None = None,
    model: str | BaseLlm | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        setup_telemetry(settings)
        container = build_container(settings, session_service, model)
        if isinstance(container.session_service, DatabaseSessionService):
            await container.session_service.prepare_tables()
        app.state.container = container
        try:
            yield
        finally:
            await close_container(container)

    app = FastAPI(
        title="Asesor automotriz virtual",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-User-Id", "Authorization", "X-Debug-Fault"],
    )

    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(sessions.router)
    app.include_router(chat.router)

    return app
